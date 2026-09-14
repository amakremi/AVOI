"""Evidence collectors for the controlled IAM testbed.

Each collector implements ONE evidence action. It may only use the sources that the action represents:
Keycloak Admin REST API, the documentary evidence repository (HTTP), or the Linux host shell (docker exec).
Collectors NEVER read testbed/state/hidden (systems of record used only by the ground-truth oracle) and never
query PostgreSQL directly.

Every collector returns an EvidenceObservation-compatible dict:
  outcome, raw (structured artifact), bytes_read, records, api_calls, parser, privacy_categories
Wall-clock acquisition time is measured by the caller (run_testbed.py / live environment).
"""
from __future__ import annotations

import csv
import hashlib
import io
from datetime import datetime, timezone

from testbed.keycloak.kc import IOStats, KeycloakAdmin, browser_login, docker_exec, repo_get

DAY_MS = 86_400_000
APP_HOST = "avoi-app-host"
PARSER_VERSION = "iam-collectors/1.0"

# field-name -> sensitive category (schema in config/evidence_actions.yaml)
FIELD_CATEGORY = {
    "username": "user_identifier", "user": "user_identifier", "userId": "user_identifier", "subject": "user_identifier",
    "members": "user_identifier", "scope": "user_identifier",
    "email": "email_address",
    "ipAddress": "ip_address",
    "host": "host_device_identifier", "shadow_entry": "host_device_identifier",
    "roles": "role_group_membership", "group": "role_group_membership", "privileged": "role_group_membership",
    "decision": "role_group_membership",
    "event_time": "authentication_event", "last_login": "authentication_event", "login_client": "authentication_event",
    "test_result": "authentication_event",
    "termination_date": "hr_employment_record", "employee_id": "hr_employment_record",
    "emergency_ticket": "security_incident_information",
}


def privacy_categories(raw) -> list[str]:
    found = set()

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in FIELD_CATEGORY and v not in (None, [], {}, ""):
                    found.add(FIELD_CATEGORY[k])
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(raw)
    return sorted(found)


def _ms(iso: str) -> int:
    return int(datetime.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S" if "T" in iso else "%Y-%m-%d")
               .replace(tzinfo=timezone.utc).timestamp() * 1000) if len(iso) > 10 else \
        int(datetime.strptime(iso, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


class IAMCollectors:
    def __init__(self, realm: str, t0_ms: int, params: dict, kc: KeycloakAdmin | None = None,
                 test_password: str | None = None):
        # test_password: credential issued to the assessor for SP 800-53A TEST procedures (assessor credential file)
        self.realm, self.t0, self.p = realm, t0_ms, params
        self.test_password = test_password
        self.kc = kc or KeycloakAdmin()
        self.window_from = t0_ms - params["event_window_days"] * DAY_MS

    # ------------------------------------------------------------------ source helpers (each call is metered)
    def _repo(self, rel, st):
        return repo_get(f"{self.realm}/{rel}", st)

    def _users(self, st, **q):
        return self.kc.get(f"/{self.realm}/users", st, max=5000, briefRepresentation="false", **q)

    @staticmethod
    def _attr(u, k):
        v = (u.get("attributes") or {}).get(k)
        return v[0] if v else None

    def _is_human(self, u):
        return self._attr(u, "account_type") is None

    def _effective_roles(self, uid, st):
        return {r["name"] for r in self.kc.get(f"/{self.realm}/users/{uid}/role-mappings/realm/composite", st)}

    def _direct_and_group_priv(self, st):
        direct = self.kc.get(f"/{self.realm}/roles/priv_admin/users", st, max=5000)
        groups = self.kc.get(f"/{self.realm}/groups", st)
        admins = next((g for g in groups if g["name"] == "Admins"), None)
        members = self.kc.get(f"/{self.realm}/groups/{admins['id']}/members", st, max=5000) if admins else []
        return direct, members

    def _login_events(self, st, max_results=5000, user=None):
        q = {"type": "LOGIN", "max": max_results}
        if user:
            q["user"] = user
        ev = self.kc.get(f"/{self.realm}/events", st, **q)
        return [e for e in ev if self.window_from <= e["time"] < self.t0]

    def _admin_events(self, st, operation):
        ev = self.kc.get(f"/{self.realm}/admin-events", st, operationTypes=operation,
                         resourceTypes=["REALM_ROLE_MAPPING", "GROUP_MEMBERSHIP"], max=5000)
        return [e for e in ev if e["time"] < self.t0]

    def _approvals(self, st):
        text = self._repo("registers/privileged_access_approvals.csv", st)
        if text is None:
            return None, None
        meta = self._repo("registers/privileged_access_approvals.meta.json", st) or {}
        rows = list(csv.DictReader(io.StringIO(text)))
        return rows, meta

    def _approved(self, rows):
        ok = set()
        for r in rows or []:
            if r.get("expiry_date") and _ms(r["expiry_date"]) < self.t0:
                continue
            ok.add(r["username"])
        return ok

    def _effective_priv_users(self, st):
        users = [u for u in self._users(st) if u["enabled"]]
        priv = []
        for u in users:
            if "priv_admin" in self._effective_roles(u["id"], st):
                priv.append(u)
        return priv

    # ------------------------------------------------------------------ dispatcher
    def collect(self, action_id: str) -> dict:
        st = IOStats()
        outcome, raw = getattr(self, action_id)(st)
        return {"outcome": outcome, "raw": raw, "bytes_read": st.bytes_read, "records": st.records,
                "api_calls": st.calls, "parser": f"{PARSER_VERSION}:{action_id}",
                "privacy_categories": sorted(st.categories),          # categories in payloads actually accessed
                "privacy_categories_in_artifact": privacy_categories(raw)}

    # ================================================================== IAM-01 MFA
    def doc_mfa_policy(self, st):
        d = self._repo("policies/authentication_standard.json", st)
        if d is None:
            return "not_found", {"document": None}
        mand = any(c.get("topic") == "mfa_privileged_accounts" and c.get("requirement") == "mandatory" for c in d["clauses"])
        return ("mandates_priv_mfa" if mand else "no_priv_mfa_clause"), {"document": d["document"], "clauses": [c["id"] for c in d["clauses"]]}

    def doc_mfa_exception_register(self, st):
        d = self._repo("registers/mfa_exceptions.json", st)
        if d is None:
            return "not_found", {"register": None}
        return ("exceptions_listed" if d["rows"] else "no_exceptions"), {"rows": d["rows"]}

    def kc_realm_browser_flow(self, st):
        realm = self.kc.get(f"/{self.realm}", st)
        alias = realm["browserFlow"]
        execs = self.kc.get(f"/{self.realm}/authentication/flows/{alias}/executions", st)
        sub_req, otp_req, role_cond, user_cfg = None, None, None, None
        in_2fa = False
        for e in execs:
            if e["level"] == 1:
                in_2fa = "Conditional 2FA" in str(e.get("displayName"))
                if in_2fa:
                    sub_req = e["requirement"]
            elif in_2fa:
                if e.get("providerId") == "auth-otp-form":
                    otp_req = e["requirement"]
                elif e.get("providerId") == "conditional-user-role" and e["requirement"] != "DISABLED":
                    cfg = self.kc.get(f"/{self.realm}/authentication/config/{e['authenticationConfig']}", st)
                    role_cond = cfg["config"].get("condUserRole")
                elif e.get("providerId") == "conditional-user-configured":
                    user_cfg = e["requirement"]
        raw = {"browser_flow": alias, "subflow_requirement": sub_req, "otp_form": otp_req, "role_condition": role_cond,
               "user_configured_condition": user_cfg}
        if sub_req in (None, "DISABLED") or otp_req in (None, "DISABLED"):
            return "otp_not_enforced", raw
        if role_cond == "priv_admin" and otp_req == "REQUIRED":
            return "otp_enforced_priv_role", raw
        if role_cond:
            return "otp_conditional_other_role", raw
        return "otp_not_enforced", raw

    def kc_client_flow_overrides(self, st):
        clients = self.kc.get(f"/{self.realm}/clients", st)
        ov = [{"client": c["clientId"], "override": c.get("authenticationFlowBindingOverrides")}
              for c in clients if c.get("authenticationFlowBindingOverrides")]
        return ("overrides_present" if ov else "no_overrides"), {"overrides": ov}

    def _priv_candidates(self, st):
        direct, members = self._direct_and_group_priv(st)
        seen, out = set(), []
        for u in direct + members:
            if u["id"] in seen or not u.get("enabled", True):
                continue
            seen.add(u["id"])
            full = self.kc.get(f"/{self.realm}/users/{u['id']}", st)
            if self._is_human(full):
                out.append(full)
        return sorted(out, key=lambda x: x["username"])

    def test_mfa_login_sample(self, st, password: str | None = None):
        cands = self._priv_candidates(st)
        k = self.p["login_test_sample_size"]
        rng_key = int(hashlib.sha256(f"{self.realm}|mfa-sample".encode()).hexdigest()[:8], 16)
        order = sorted(cands, key=lambda u: hashlib.sha256(f"{rng_key}|{u['username']}".encode()).hexdigest())[:k]
        results = []
        for u in order:
            res = browser_login(self.realm, "portal", u["username"], password or self.test_password)
            st.add(res.bytes, 1, {"user_identifier", "authentication_event"})
            results.append({"username": u["username"], "test_result": res.outcome})
        bypass = any(r["test_result"] == "authenticated" for r in results)
        return ("bypass_observed" if bypass else "all_challenged"), {"client": "portal", "tests": results}

    def kc_priv_user_credentials(self, st):
        out = []
        for u in self._priv_candidates(st):
            creds = self.kc.get(f"/{self.realm}/users/{u['id']}/credentials", st)
            out.append({"username": u["username"], "otp": any(c["type"] == "otp" for c in creds)})
        return ("all_priv_have_otp" if all(x["otp"] for x in out) else "some_priv_without_otp"), {"privileged": out}

    def kc_auth_events_priv(self, st):
        ids = {u["id"]: u["username"] for u in self._priv_candidates(st)}
        ev = [e for e in self._login_events(st) if e.get("userId") in ids]
        raw = {"events": [{"username": ids[e["userId"]], "login_client": e.get("clientId"), "ipAddress": e.get("ipAddress"),
                           "event_time": e["time"]} for e in ev]}
        if not ev:
            return "no_events", raw
        return ("nondefault_client_logins" if any(e.get("clientId") != "portal" for e in ev) else "only_default_client_logins"), raw

    # ================================================================== IAM-02 termination
    def doc_offboarding_procedure(self, st):
        d = self._repo("procedures/offboarding.json", st)
        return ("documented_with_sla" if d and d.get("revoke_access_sla_hours") else "not_found"), {"document": d and d["document"]}

    def _terminations(self, st):
        text = self._repo("hr/terminations_last_180d.csv", st)
        rows = list(csv.DictReader(io.StringIO(text or "")))
        cutoff = self.t0 - self.p["termination_grace_days"] * DAY_MS
        return [r for r in rows if _ms(r["termination_date"]) <= cutoff]

    def hr_termination_feed(self, st):
        rows = self._terminations(st)
        return ("terminations_present" if rows else "no_terminations"), {
            "rows": [{"employee_id": r["employee_id"], "termination_date": r["termination_date"]} for r in rows]}

    def ticket_offboarding_records(self, st):
        rows = self._terminations(st)
        t = self._repo("tickets/tickets_export.json", st)
        if t is None:
            return "not_found", {"tickets": None}
        closed = {x["subject"] for x in t["rows"] if x["type"] == "offboarding" and x["status"] == "closed"}
        status = [{"employee_id": r["employee_id"], "closed_ticket": r["employee_id"] in closed} for r in rows]
        return ("all_closed" if all(s["closed_ticket"] for s in status) else "open_or_missing"), {"status": status}

    def kc_disabled_accounts(self, st):
        users = self.kc.get(f"/{self.realm}/users", st, enabled="false", max=5000, briefRepresentation="true")
        users = [u for u in users if not u.get("enabled", True)]
        return ("some_disabled" if users else "none_disabled"), {"disabled": [{"username": u["username"]} for u in users]}

    def recon_hr_vs_directory(self, st):
        terms = self._terminations(st)
        users = self._users(st)
        by_eid = {self._attr(u, "employee_id"): u for u in users if self._attr(u, "employee_id")}
        unlinked = [u["username"] for u in users if u["enabled"] and self._is_human(u) and not self._attr(u, "employee_id")]
        res, missing = [], []
        for r in terms:
            u = by_eid.get(r["employee_id"])
            if u is None:
                missing.append(r["employee_id"])
            res.append({"employee_id": r["employee_id"], "termination_date": r["termination_date"],
                        "username": u and u["username"], "email": u and u.get("email"), "enabled": u and u["enabled"]})
        raw = {"reconciliation": res, "unlinked_enabled_accounts": [{"username": x} for x in unlinked]}
        if any(x["enabled"] for x in res):
            return "enabled_terminated_found", raw
        if missing and unlinked:
            return "unlinked_accounts_present", raw
        return "all_terminated_disabled", raw

    def kc_login_events_post_termination(self, st):
        terms = self._terminations(st)
        hits = []
        for r in terms:
            us = self.kc.get(f"/{self.realm}/users", st, q=f"employee_id:{r['employee_id']}", briefRepresentation="true")
            for u in us:
                for e in self._login_events(st, user=u["id"]):
                    if e["time"] > _ms(r["termination_date"]):
                        hits.append({"employee_id": r["employee_id"], "username": u["username"], "event_time": e["time"],
                                     "ipAddress": e.get("ipAddress")})
        return ("post_termination_logins" if hits else "none_observed"), {"hits": hits}

    # ================================================================== IAM-03 privileged authorization
    def doc_priv_access_procedure(self, st):
        d = self._repo("procedures/privileged_access.json", st)
        return ("documented" if d else "not_found"), {"document": d and d["document"]}

    def approval_register(self, st):
        rows, meta = self._approvals(st)
        if rows is None:
            return "register_stale_or_absent", {"register": None}
        exported = _ms(meta["exported"]) if meta.get("exported") else 0
        current = self.t0 - exported <= 30 * DAY_MS
        return ("register_current" if current else "register_stale_or_absent"), {
            "exported": meta.get("exported"), "rows": [{"username": r["username"]} for r in rows]}

    def recon_direct_members_vs_approvals(self, st):
        rows, _ = self._approvals(st)
        ok = self._approved(rows)
        direct, _m = self._direct_and_group_priv(st)
        bad = [u["username"] for u in direct if u["username"] not in ok]
        return ("unapproved_direct_found" if bad else "all_direct_approved"), {"privileged": [{"username": u["username"]} for u in direct], "unapproved": bad}

    def recon_group_members_vs_approvals(self, st):
        rows, _ = self._approvals(st)
        ok = self._approved(rows)
        _d, members = self._direct_and_group_priv(st)
        bad = [u["username"] for u in members if u["username"] not in ok]
        return ("unapproved_group_found" if bad else "all_group_approved"), {"members": [u["username"] for u in members], "unapproved": bad}

    def kc_composite_role_analysis(self, st):
        roles = self.kc.get(f"/{self.realm}/roles", st, briefRepresentation="false")
        paths = []
        for r in roles:
            if r.get("composite"):
                comps = {c["name"] for c in self.kc.get(f"/{self.realm}/roles/{r['name']}/composites", st)}
                if "priv_admin" in comps:
                    holders = self.kc.get(f"/{self.realm}/roles/{r['name']}/users", st, max=5000)
                    paths.append({"roles": r["name"], "members": [h["username"] for h in holders]})
        present = any(p_["members"] for p_ in paths)
        return ("composite_path_members_present" if present else "no_composite_paths"), {"composite_paths": paths}

    def admin_events_role_grants(self, st):
        ev = [e for e in self._admin_events(st, "CREATE") if e["time"] >= self.window_from]
        raw = {"grants": [{"resourcePath": e.get("resourcePath"), "event_time": e["time"],
                           "ipAddress": (e.get("authDetails") or {}).get("ipAddress"), "roles": True} for e in ev]}
        return ("recent_grants_present" if ev else "no_recent_grants"), raw

    def recon_effective_vs_approvals(self, st):
        rows, _ = self._approvals(st)
        ok = self._approved(rows)
        priv = self._effective_priv_users(st)
        bad = [u["username"] for u in priv if u["username"] not in ok]
        return ("unapproved_effective_found" if bad else "all_effective_approved"), {
            "privileged": [{"username": u["username"], "email": u.get("email")} for u in priv], "unapproved": bad}

    # ================================================================== IAM-04 dormancy
    def doc_account_lifecycle_standard(self, st):
        d = self._repo("standards/account_lifecycle.json", st)
        return ("dormancy_rule_documented" if d and d.get("disable_inactive_after_days") else "not_found"), {"document": d and d["document"]}

    def iam_dormancy_report(self, st):
        d = self._repo("reports/dormant_accounts_report.json", st)
        if d is None or self.t0 - _ms(d["generated"]) > 30 * DAY_MS:
            return "report_stale_or_absent", {"generated": d and d["generated"]}
        return ("report_current_dormant_listed" if d["rows"] else "report_current_no_dormant"), {"generated": d["generated"], "rows": d["rows"]}

    def _old_enabled_humans(self, users):
        thr = self.t0 - self.p["dormancy_threshold_days"] * DAY_MS
        return [u for u in users if u["enabled"] and self._is_human(u) and u.get("createdTimestamp", 0) < thr]

    def kc_user_inventory_age(self, st):
        old = self._old_enabled_humans(self._users(st))
        return ("old_enabled_accounts_present" if old else "no_old_enabled_accounts"), {
            "accounts": [{"username": u["username"], "email": u.get("email")} for u in old]}

    def recon_events_api_vs_inventory(self, st):
        old = self._old_enabled_humans(self._users(st))
        ev = self._login_events(st, max_results=self.p["events_api_page_size"])
        seen = {e.get("userId") for e in ev}
        unseen = [u["username"] for u in old if u["id"] not in seen]
        raw = {"page_size": self.p["events_api_page_size"], "events": [{"userId": e.get("userId"), "event_time": e["time"],
                                                                          "ipAddress": e.get("ipAddress")} for e in ev],
               "unseen": [{"username": x} for x in unseen]}
        return ("unseen_old_accounts" if unseen else "all_old_accounts_active"), raw

    def siem_login_export(self, st):
        text = self._repo("siem/last_login_export.csv", st)
        if text is None:
            return "export_absent", {"export": None}
        thr = self.t0 - self.p["dormancy_threshold_days"] * DAY_MS
        dormant = []
        for r in csv.DictReader(io.StringIO(text)):
            if _ms(r["account_created"]) < thr and (not r["last_login"] or _ms(r["last_login"]) < thr):
                dormant.append({"username": r["username"], "last_login": r["last_login"]})
        return ("dormant_in_export" if dormant else "no_dormant_in_export"), {"dormant": dormant}

    # ================================================================== IAM-05 break-glass
    def doc_breakglass_procedure(self, st):
        d = self._repo("procedures/breakglass.json", st)
        return ("documented" if d else "not_found"), {"document": d and d["document"]}

    def recon_register_vs_kc_attribute(self, st):
        reg = self._repo("registers/breakglass_accounts.json", st)
        tagged = self.kc.get(f"/{self.realm}/users", st, q="account_type:break_glass", briefRepresentation="true")
        tagged_names = sorted(u["username"] for u in tagged)
        raw = {"tagged": [{"username": x} for x in tagged_names], "register": reg and reg["rows"]}
        if reg is None:
            return "register_absent", raw
        return ("consistent" if sorted(r["username"] for r in reg["rows"]) == tagged_names else "register_mismatch"), raw

    def kc_nonpersonal_priv_accounts(self, st):
        users = [u for u in self._users(st) if u["enabled"] and not self._attr(u, "employee_id") and self._is_human(u)]
        bad = [u["username"] for u in users if "priv_admin" in self._effective_roles(u["id"], st)]
        return ("unidentified_nonpersonal_priv" if bad else "all_identified"), {"privileged": [{"username": x} for x in bad]}

    def host_local_emergency_account(self, st):
        out = docker_exec(APP_HOST, "getent shadow bgroot || true", st).strip()
        if not out:
            return "absent", {"host": "app-host", "shadow_entry": None}
        pw = out.split(":")[1]
        locked = pw.startswith("!") or pw.startswith("*") or pw == ""
        return ("locked" if locked else "unlocked"), {"host": "app-host", "shadow_entry": {"username": "bgroot", "locked": locked}}

    def emergency_ticket_records(self, st):
        t = self._repo("tickets/tickets_export.json", st)
        if t is None:
            return "not_found", {"tickets": None}
        em = [x for x in t["rows"] if x["type"] == "emergency"]
        open_ = [x for x in em if x["status"] == "open"]
        return ("open_emergency_ticket" if open_ else "no_open_emergency"), {"emergency_ticket": em}

    def kc_breakglass_login_events(self, st):
        tagged = self.kc.get(f"/{self.realm}/users", st, q="account_type:break_glass", briefRepresentation="true")
        hits = []
        for u in tagged:
            for e in self._login_events(st, user=u["id"]):
                hits.append({"username": u["username"], "event_time": e["time"], "ipAddress": e.get("ipAddress")})
        return ("bg_logins_present" if hits else "no_bg_logins"), {"logins": hits}

    # ================================================================== IAM-06 access review
    def doc_access_review_policy(self, st):
        d = self._repo("policies/access_review.json", st)
        return ("periodic_review_documented" if d else "not_found"), {"document": d and d["document"]}

    def _review(self, st):
        return self._repo("reviews/latest_privileged_access_review.json", st)

    def access_review_record(self, st):
        rv = self._review(st)
        if rv is None:
            return "not_found", {"review": None}
        current = self.t0 - _ms(rv["completed"]) <= self.p["access_review_max_age_days"] * DAY_MS
        return ("current_signed" if current and rv.get("signed_by") else "stale_or_unsigned"), {
            "completed": rv["completed"], "signed": bool(rv.get("signed_by")), "scope": rv["scope"]}

    def recon_review_scope_vs_effective(self, st):
        rv = self._review(st)
        if rv is None:
            return "no_review_to_compare", {"review": None}
        priv = self._effective_priv_users(st)
        gaps = [u["username"] for u in priv if u["username"] not in set(rv["scope"])]
        return ("scope_gaps" if gaps else "scope_complete"), {"scope": rv["scope"], "privileged": [u["username"] for u in priv], "gaps": gaps}

    def recon_revocations_vs_directory(self, st):
        rv = self._review(st)
        if rv is None:
            return "no_review_to_compare", {"review": None}
        revokes = [d["username"] for d in rv["decisions"] if d["decision"] == "revoke"]
        if not revokes:
            return "no_revocations", {"decisions": rv["decisions"]}
        still = []
        for name in revokes:
            us = self.kc.get(f"/{self.realm}/users", st, username=name, exact="true", briefRepresentation="true")
            if us and "priv_admin" in self._effective_roles(us[0]["id"], st):
                still.append(name)
        return ("unimplemented_revocations" if still else "all_revocations_implemented"), {
            "decision": revokes, "still_privileged": [{"username": x} for x in still]}

    def exception_ticket_records(self, st):
        t = self._repo("tickets/tickets_export.json", st)
        if t is None:
            return "not_found", {"tickets": None}
        ex = [x for x in t["rows"] if x["type"] == "access_exception" and x["status"] == "open"]
        return ("exceptions_tracked" if ex else "no_exception_tickets"), {"exceptions": [{"subject": x["subject"]} for x in ex]}

    def admin_events_role_removals(self, st):
        rv = self._review(st)
        since = _ms(rv["completed"]) if rv else self.window_from
        ev = [e for e in self._admin_events(st, "DELETE") if e["time"] >= since]
        return ("removals_after_review" if ev else "no_removals_after_review"), {
            "removals": [{"resourcePath": e.get("resourcePath"), "event_time": e["time"], "roles": True} for e in ev]}

