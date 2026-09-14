"""Apply a scenario specification to the live testbed.

Order of operations (all through public interfaces, audited where Keycloak audits):
  1. realm import (roles, groups, clients, users with password credentials; no role/group grants)
  2. authentication flow configuration + client flow-binding overrides
  3. role / group grants via the admin API in chronological order -> admin events, time-shifted in PostgreSQL
  4. user creation timestamps shifted in PostgreSQL
  5. real browser-flow logins (OTP answered / enrolled with TOTP) -> login events, time-shifted
  6. revocations, disables, deletions via the admin API -> admin events, time-shifted
  7. Linux host local emergency account state
  8. documentary evidence repository exports (served over HTTP)
  9. hidden systems of record (identity registry, HR, approvals, reviews, tickets) -> testbed/state/hidden
     (read by the ground-truth oracle only; never served and never readable by evidence collectors)

Time shifting emulates organisational history; it is disclosed in docs/METHODOLOGY.md.
"""
from __future__ import annotations

import csv
import io
import json
import shutil
import time
import urllib.parse as up
from datetime import datetime, timezone
from pathlib import Path

from testbed.keycloak.kc import KeycloakAdmin, browser_login, db, docker_exec

ROOT = Path(__file__).resolve().parents[2]
REPO_DIR = ROOT / "testbed" / "state" / "evidence_repo"
HIDDEN_DIR = ROOT / "testbed" / "state" / "hidden"
DAY_MS = 86_400_000
APP_HOST = "avoi-app-host"


def iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Applier:
    def __init__(self, kc: KeycloakAdmin | None = None):
        self.kc = kc or KeycloakAdmin()
        self.log: list[str] = []

    # ------------------------------------------------------------------ helpers
    # Events are identified by ID sets (not by comparing clocks: the Docker VM clock may drift from the host clock).
    def _new_ids(self, conn, table: str, realm_id: str, known: set) -> list:
        ids = [r[0] for r in conn.run(f"SELECT id FROM {table} WHERE realm_id = :r", r=realm_id)]
        return [i for i in ids if i not in known]

    def _shift_admin_events(self, conn, realm_id: str, known: set, target_ms: int):
        new = self._new_ids(conn, "admin_event_entity", realm_id, known)
        for i in new:
            conn.run("UPDATE admin_event_entity SET admin_event_time = :t WHERE id = :i", t=target_ms, i=i)
        known.update(new)

    def _shift_user_events(self, conn, realm_id: str, known: set, target_ms: int):
        new = self._new_ids(conn, "event_entity", realm_id, known)
        for i in new:
            conn.run("UPDATE event_entity SET event_time = :t WHERE id = :i", t=target_ms, i=i)
        known.update(new)

    @staticmethod
    def db_now_ms(conn) -> int:
        return int(conn.run("SELECT (extract(epoch from clock_timestamp()) * 1000)::bigint")[0][0])

    def _ts(self, t0: int, days_ago: float, jitter_s: int = 0) -> int:
        return int(t0 - days_ago * DAY_MS + jitter_s * 1000)

    # ------------------------------------------------------------------ main
    def apply(self, spec: dict) -> dict:
        kc, realm = self.kc, spec["scenario_id"]
        _c = db()
        t0 = self.db_now_ms(_c)  # history reference time on the Docker VM clock (same clock as Keycloak events)
        _c.close()
        pw = spec["password"]
        kc.delete(f"/{realm}")
        roles = [{"name": "priv_admin", "description": "privileged administration"},
                 {"name": "sec_admin", "description": "security administration"}]
        users = []
        for a in spec["accounts"]:
            attrs = {}
            if a["employee_id_attr"] and a["person_id"]:
                person = next(p for p in spec["persons"] if p["person_id"] == a["person_id"])
                attrs["employee_id"] = [person["employee_id"]]
                attrs["department"] = [person["dept"]]
            if a["account_type_attr"]:
                attrs["account_type"] = [a["account_type_attr"]]
            person = next((p for p in spec["persons"] if p["person_id"] == a["person_id"]), None)
            users.append({"username": a["username"], "enabled": True, "emailVerified": True,
                          "firstName": person["first"] if person else a["username"],
                          "lastName": person["last"] if person else "account",
                          "email": person["email"] if person else f"{a['username']}@corp.test",
                          "attributes": attrs,
                          "requiredActions": ["CONFIGURE_TOTP"] if a["otp_required_action"] else [],
                          "credentials": [{"type": "password", "value": pw, "temporary": False}]})
        clients = [{"clientId": c["clientId"], "publicClient": True, "standardFlowEnabled": True,
                    "directAccessGrantsEnabled": False, "redirectUris": [REDIRECT_URI]} for c in spec["clients"]]
        rep = {"realm": realm, "enabled": True, "eventsEnabled": True, "adminEventsEnabled": True,
               "adminEventsDetailsEnabled": True, "otpPolicyCodeReusable": True, "sslRequired": "none",
               "roles": {"realm": roles}, "groups": [{"name": "Admins", "realmRoles": ["priv_admin"]}],
               "clients": clients, "bruteForceProtected": False}
        kc.post("", rep)
        # Keycloak 26 user profile drops unmanaged attributes by default; enable them before importing users
        profile = kc.get(f"/{realm}/users/profile")
        profile["unmanagedAttributePolicy"] = "ENABLED"
        kc.put(f"/{realm}/users/profile", profile)
        kc.post(f"/{realm}/partialImport", {"ifResourceExists": "FAIL", "users": users})
        kc.put(f"/{realm}/events/config", {"eventsEnabled": True, "adminEventsEnabled": True,
                                             "adminEventsDetailsEnabled": True, "eventsListeners": ["jboss-logging"],
                                             "enabledEventTypes": []})
        realm_id = kc.get(f"/{realm}")["id"]
        if spec["composite_role"]:
            kc.post(f"/{realm}/roles", {"name": "ops_superuser", "description": "operations superuser"})
            priv = kc.get(f"/{realm}/roles/priv_admin")
            kc.post(f"/{realm}/roles/ops_superuser/composites", [priv])
        self._configure_flows(realm, spec)
        uid = {u["username"]: u["id"] for u in kc.get(f"/{realm}/users", max=2000, briefRepresentation="true")}
        gid = {g["name"]: g["id"] for g in kc.get(f"/{realm}/groups")}
        role_rep = {r["name"]: r for r in kc.get(f"/{realm}/roles")}
        conn = db()
        try:
            known_admin = set(self._new_ids(conn, "admin_event_entity", realm_id, set()))
            known_ev = set(self._new_ids(conn, "event_entity", realm_id, set()))
            # 3. grants
            for gr in sorted(spec["grants"], key=lambda x: -x["days_ago"]):
                self._shift_admin_events(conn, realm_id, known_admin, t0)  # absorb unrelated events at T0
                u = uid[gr["username"]]
                if gr["path"] == "direct":
                    kc.post(f"/{realm}/users/{u}/role-mappings/realm", [role_rep["priv_admin"]])
                elif gr["path"] == "group":
                    kc.put(f"/{realm}/users/{u}/groups/{gid['Admins']}")
                elif gr["path"] == "composite":
                    kc.post(f"/{realm}/users/{u}/role-mappings/realm", [role_rep["ops_superuser"]])
                self._shift_admin_events(conn, realm_id, known_admin, self._ts(t0, gr["days_ago"], 3600))
            # 4. creation timestamps
            for a in spec["accounts"]:
                conn.run("UPDATE user_entity SET created_timestamp = :t WHERE id = :u",
                         t=self._ts(t0, a["created_days_ago"]), u=uid[a["username"]])
            kc.post(f"/{realm}/clear-user-cache")
            # 5. login history (chronological)
            secrets: dict[str, str] = {}
            logins = sorted(((lg["days_ago"], a["username"], lg["client"]) for a in spec["accounts"] for lg in a["logins"]),
                            key=lambda x: -x[0])
            for i, (days_ago, uname, client) in enumerate(logins):
                res = browser_login(realm, client, uname, pw, secrets.get(uname), complete_otp=True)
                if res.otp_secret:
                    secrets[uname] = res.otp_secret
                if res.outcome != "authenticated":
                    self.log.append(f"{realm}: history login {uname}@{client} -> {res.outcome} {res.detail[:80]}")
                self._shift_user_events(conn, realm_id, known_ev, self._ts(t0, days_ago, 8 * 3600 + i * 7))
            # 6. revocations, disables, deletions
            for rm in sorted(spec["removals"], key=lambda x: -x["days_ago"]):
                self._shift_admin_events(conn, realm_id, known_admin, t0)
                u = uid[rm["username"]]
                eff = {r["name"] for r in kc.get(f"/{realm}/users/{u}/role-mappings/realm")}
                for rn in ("priv_admin", "ops_superuser"):
                    if rn in eff:
                        kc.req("DELETE", f"/{realm}/users/{u}/role-mappings/realm", json=[role_rep[rn]])
                if gid["Admins"] in {g["id"] for g in kc.get(f"/{realm}/users/{u}/groups")}:
                    kc.delete(f"/{realm}/users/{u}/groups/{gid['Admins']}")
                self._shift_admin_events(conn, realm_id, known_admin, self._ts(t0, rm["days_ago"], 3600))
            persons = {p["person_id"]: p for p in spec["persons"]}
            for a in spec["accounts"]:
                if a["enabled"] and not a["deleted"]:
                    continue
                self._shift_admin_events(conn, realm_id, known_admin, t0)
                p = persons.get(a["person_id"])
                when = max(0, (p["term_days_ago"] - 1) if (p and p["term_days_ago"]) else 10)
                if a["deleted"]:
                    kc.delete(f"/{realm}/users/{uid[a['username']]}")
                else:
                    kc.put(f"/{realm}/users/{uid[a['username']]}", {"enabled": False})
                self._shift_admin_events(conn, realm_id, known_admin, self._ts(t0, when, 3600))
            kc.post(f"/{realm}/clear-user-cache")
            kc.post(f"/{realm}/clear-realm-cache")
            # assessment time T0: end of setup on the database clock; all history events are strictly earlier
            t_assess = self.db_now_ms(conn) + 1000
        finally:
            conn.close()
        self._apply_host(spec)
        self._write_repo(spec, t0)
        self._write_hidden(spec, t0, realm_id, t_assess)
        return {"realm": realm, "realm_id": realm_id, "t0_ms": t_assess, "history_reference_ms": t0, "setup_log": list(self.log)}

    # ------------------------------------------------------------------ flows
    def _configure_flows(self, realm: str, spec: dict):
        kc = self.kc
        kc.post(f"/{realm}/authentication/flows/browser/copy", {"newName": "browser-avoi"})
        sub = up.quote("browser-avoi Browser - Conditional 2FA", safe="")
        kc.post(f"/{realm}/authentication/flows/{sub}/executions/execution", {"provider": "conditional-user-role"})
        mode = spec["flow_mode"]
        for e in kc.get(f"/{realm}/authentication/flows/browser-avoi/executions"):
            pid = e.get("providerId")
            if pid == "conditional-user-role":
                kc.post(f"/{realm}/authentication/executions/{e['id']}/config",
                        {"alias": "privileged-role-condition",
                         "config": {"condUserRole": "sec_admin" if mode == "wrong_role" else "priv_admin", "negate": "false"}})
                e["requirement"] = "REQUIRED"
                kc.put(f"/{realm}/authentication/flows/browser-avoi/executions", e)
            elif pid == "conditional-user-configured" and e["level"] == 2 and "2FA" not in str(e.get("displayName")):
                # only the condition inside the 2FA subflow is disabled (identified by its parent below)
                pass
            elif pid == "auth-otp-form":
                e["requirement"] = "REQUIRED"
                kc.put(f"/{realm}/authentication/flows/browser-avoi/executions", e)
            elif e.get("displayName") == "browser-avoi Browser - Conditional 2FA" and mode == "disabled":
                e["requirement"] = "DISABLED"
                kc.put(f"/{realm}/authentication/flows/browser-avoi/executions", e)
        # disable the "user configured" condition inside the 2FA subflow (role condition replaces it)
        execs = kc.get(f"/{realm}/authentication/flows/browser-avoi/executions")
        in_2fa = False
        for e in execs:
            if e["level"] == 1:
                in_2fa = e.get("displayName") == "browser-avoi Browser - Conditional 2FA"
            elif in_2fa and e.get("providerId") == "conditional-user-configured":
                e["requirement"] = "DISABLED"
                kc.put(f"/{realm}/authentication/flows/browser-avoi/executions", e)
        rep = kc.get(f"/{realm}")
        rep["browserFlow"] = "browser-avoi"
        rep["otpPolicyCodeReusable"] = True  # testbed history simulation performs several logins within one TOTP period
        kc.put(f"/{realm}", rep)
        flows = {f["alias"]: f["id"] for f in kc.get(f"/{realm}/authentication/flows")}
        for c in spec["clients"]:
            if not c["override"]:
                continue
            if c["override"] == "benign_otp":
                kc.post(f"/{realm}/authentication/flows/browser-avoi/copy", {"newName": "browser-kiosk"})
                flows = {f["alias"]: f["id"] for f in kc.get(f"/{realm}/authentication/flows")}
                target = flows["browser-kiosk"]
            else:
                target = flows["browser"]
            cl = kc.get(f"/{realm}/clients", clientId=c["clientId"])[0]
            cl["authenticationFlowBindingOverrides"] = {"browser": target}
            kc.put(f"/{realm}/clients/{cl['id']}", cl)

    # ------------------------------------------------------------------ Linux host
    def _apply_host(self, spec: dict):
        h = spec["host"]
        cmd = "deluser bgroot >/dev/null 2>&1; "
        if h["bgroot_exists"]:
            cmd += "adduser -D -s /bin/sh bgroot >/dev/null 2>&1; "
            if not h["bgroot_locked"]:
                cmd += f"echo 'bgroot:{spec['password']}' | chpasswd >/dev/null 2>&1; "
        cmd += "echo done"
        docker_exec(APP_HOST, cmd)

    # ------------------------------------------------------------------ documentary evidence repository
    def _write_repo(self, spec: dict, t0: int):
        base = REPO_DIR / spec["scenario_id"]
        if base.exists():
            shutil.rmtree(base)
        base.mkdir(parents=True)
        docs = spec["documents"]
        persons = {p["person_id"]: p for p in spec["persons"]}
        acc = {a["username"]: a for a in spec["accounts"]}

        def wj(rel, obj):
            p = base / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(obj, indent=1), encoding="utf-8")

        def wc(rel, header, rows):
            p = base / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            buf = io.StringIO()
            w = csv.writer(buf, lineterminator="\n")
            w.writerow(header)
            w.writerows(rows)
            p.write_text(buf.getvalue(), encoding="utf-8")

        if docs["mfa_policy"] != "absent":
            clauses = [{"id": "AUTH-1", "topic": "password_complexity"}, {"id": "AUTH-2", "topic": "session_timeout"}]
            if docs["mfa_policy"] == "mandates":
                clauses.append({"id": "AUTH-3", "topic": "mfa_privileged_accounts", "requirement": "mandatory"})
            wj("policies/authentication_standard.json", {"document": "Authentication Standard", "version": "2.1",
                                                          "approved": True, "clauses": clauses})
        if docs["mfa_exception_register"]["present"]:
            wj("registers/mfa_exceptions.json", {"register": "MFA exceptions", "rows": docs["mfa_exception_register"]["rows"]})
        if docs["offboarding_procedure"]:
            wj("procedures/offboarding.json", {"document": "Offboarding Procedure", "revoke_access_sla_hours": 24})
        terms = [p for p in spec["persons"] if p["status"] == "terminated"]
        wc("hr/terminations_last_180d.csv", ["employee_id", "full_name", "email", "termination_date"],
           [[p["employee_id"], f"{p['first']} {p['last']}", p["email"], iso(t0 - p["term_days_ago"] * DAY_MS)[:10]] for p in terms])
        if docs["ticket_system"]:
            wj("tickets/tickets_export.json", {"system": "ITSM", "rows": [
                {"ticket_id": t["ticket_id"], "type": t["type"], "subject": t["subject"], "status": t["status"],
                 "opened": iso(t0 - t["opened_days_ago"] * DAY_MS),
                 "closed": iso(t0 - t["closed_days_ago"] * DAY_MS) if t["closed_days_ago"] is not None else None}
                for t in spec["tickets"]]})
        if docs["priv_access_procedure"]:
            wj("procedures/privileged_access.json", {"document": "Privileged Access Management Procedure", "approval_required": True})
        reg = spec["approval_register"]
        if reg["present"]:
            header = ["username", "approved_date"] + (["expiry_date"] if reg["has_expiry_col"] else [])
            rows = []
            for ap in spec["approvals"]:
                if ap["approved_days_ago"] < reg["lag_days"]:
                    continue  # approvals newer than the export date are not in the export
                row = [ap["username"], iso(t0 - ap["approved_days_ago"] * DAY_MS)[:10]]
                if reg["has_expiry_col"]:
                    row.append(iso(t0 + ap["expires_in_days"] * DAY_MS)[:10])
                rows.append(row)
            wc("registers/privileged_access_approvals.csv", header, rows)
            wj("registers/privileged_access_approvals.meta.json", {"exported": iso(t0 - reg["lag_days"] * DAY_MS)})
        if docs["lifecycle_standard"]:
            wj("standards/account_lifecycle.json", {"document": "Account Lifecycle Standard", "disable_inactive_after_days": 90})
        # dormancy report and SIEM export reflect login history as of their generation date
        for kind in ("dormancy_report", "siem_export"):
            d = docs[kind]
            if not d["present"]:
                continue
            lag = d["lag_days"]
            rows = []
            for a in spec["accounts"]:
                if a["account_class"] != "human" or a["deleted"] or a["created_days_ago"] <= lag:
                    continue
                past = [lg["days_ago"] for lg in a["logins"] if lg["days_ago"] >= lag]
                last = min(past) if past else None
                rows.append((a, last))
            if kind == "dormancy_report":
                dormant = [a["username"] for a, last in rows if a["enabled"] and a["created_days_ago"] > lag + 90
                           and (last is None or last > lag + 90)]
                wj("reports/dormant_accounts_report.json", {"generated": iso(t0 - lag * DAY_MS), "threshold_days": 90,
                                                            "rows": [{"username": u} for u in dormant]})
            else:
                wc("siem/last_login_export.csv", ["username", "account_created", "last_login", "export_time"],
                   [[a["username"], iso(t0 - a["created_days_ago"] * DAY_MS), iso(t0 - last * DAY_MS) if last is not None else "",
                     iso(t0 - lag * DAY_MS)] for a, last in rows])
        if docs["breakglass_procedure"]:
            wj("procedures/breakglass.json", {"document": "Emergency Access Procedure", "ticket_required": True})
        if docs["bg_register_present"]:
            wj("registers/breakglass_accounts.json", {"register": "Break-glass accounts",
                                                      "rows": [{"username": a["username"]} for a in spec["accounts"]
                                                               if a["account_class"] == "break_glass" and a.get("registered", True)]})
        if docs["access_review_policy"]:
            wj("policies/access_review.json", {"document": "Access Review Policy", "privileged_review_frequency_days": 90})
        if docs["review_export_present"]:
            rv = spec["review"]
            wj("reviews/latest_privileged_access_review.json", {
                "completed": iso(t0 - rv["days_ago"] * DAY_MS), "signed_by": "Head of IAM" if rv["signed"] else None,
                "scope": rv["scope"], "decisions": [{"username": d["username"], "decision": d["decision"]} for d in rv["decisions"]]})

    # ------------------------------------------------------------------ hidden systems of record (oracle only)
    def _write_hidden(self, spec: dict, t0: int, realm_id: str, t_assess: int):
        base = HIDDEN_DIR / spec["scenario_id"]
        base.mkdir(parents=True, exist_ok=True)
        (base / "systems_of_record.json").write_text(json.dumps({
            "t0_ms": t_assess, "history_reference_ms": t0, "realm_id": realm_id,
            "identity_registry": [{"username": a["username"], "account_class": a["account_class"], "person_id": a["person_id"],
                                   "deleted": a["deleted"]} for a in spec["accounts"]],
            "hr_system": spec["persons"],
            "approvals_system": spec["approvals"],
            "review_system": spec["review"],
            "ticket_system": spec["tickets"],
            "password": spec["password"],
        }, indent=1), encoding="utf-8")
        (base / "scenario_spec.json").write_text(json.dumps(spec, indent=1), encoding="utf-8")


REDIRECT_URI = "http://localhost/cb"



