"""Ground-truth oracle for the controlled IAM testbed.

Computes Y_c in {0,1} for each atomic objective from the ACTUAL system state:
  - live Keycloak configuration and live browser-flow login tests (exhaustive, all in-scope users x clients),
  - the complete PostgreSQL event stores (event_entity, admin_event_entity) restricted to times < T0,
  - the live Linux host /etc/shadow,
  - hidden systems of record (identity registry, HR, approvals, access reviews, tickets) and the break-glass
    register artifact itself.
The oracle is run AFTER all evidence collectors for the scenario. Its outputs are written to
data/processed/iam/ground_truth/ and are never exposed to acquisition policies.
"""
from __future__ import annotations

import json
from pathlib import Path

from testbed.keycloak.kc import KeycloakAdmin, browser_login, db, docker_exec

ROOT = Path(__file__).resolve().parents[1]
HIDDEN = ROOT / "testbed" / "state" / "hidden"
REPO = ROOT / "testbed" / "state" / "evidence_repo"
DAY_MS = 86_400_000


def evaluate(realm: str, params: dict, kc: KeycloakAdmin | None = None) -> dict:
    kc = kc or KeycloakAdmin()
    sor = json.loads((HIDDEN / realm / "systems_of_record.json").read_text(encoding="utf-8"))
    t0, realm_id, pw = sor["t0_ms"], sor["realm_id"], sor["password"]
    reg = {x["username"]: x for x in sor["identity_registry"]}
    users = {u["username"]: u for u in kc.get(f"/{realm}/users", max=5000, briefRepresentation="false")}
    eff = {name: {r["name"] for r in kc.get(f"/{realm}/users/{u['id']}/role-mappings/realm/composite")} for name, u in users.items()}
    priv_now = {n for n, roles in eff.items() if "priv_admin" in roles}
    detail = {}
    conn = db()
    try:
        # ---------------------------------------------------------------- IAM-02
        viol2 = []
        for p in sor["hr_system"]:
            if p["status"] == "terminated" and p["term_days_ago"] >= params["termination_grace_days"]:
                for acc in (a for a in sor["identity_registry"] if a["person_id"] == p["person_id"]):
                    u = users.get(acc["username"])
                    if u is not None and u["enabled"]:
                        viol2.append(acc["username"])
        detail["IAM-02-TERM-DISABLED"] = {"enabled_terminated": viol2}
        y2 = int(not viol2)

        # ---------------------------------------------------------------- IAM-03
        approved = {a["username"] for a in sor["approvals_system"] if a["expires_in_days"] > 0 and a["approved_days_ago"] >= 0}
        viol3 = sorted(n for n in priv_now if n not in approved)
        detail["IAM-03-PRIV-AUTHZ"] = {"effective_privileged": sorted(priv_now), "unapproved_or_expired": viol3}
        y3 = int(not viol3)

        # ---------------------------------------------------------------- IAM-04
        thr = t0 - params["dormancy_threshold_days"] * DAY_MS
        last = dict(conn.run("SELECT user_id, max(event_time) FROM event_entity WHERE realm_id=:r AND type='LOGIN' "
                             "AND event_time < :t GROUP BY user_id", r=realm_id, t=t0))
        created = dict(conn.run("SELECT username, created_timestamp FROM user_entity WHERE realm_id=:r", r=realm_id))
        viol4 = []
        for n, u in users.items():
            if not u["enabled"] or reg.get(n, {}).get("account_class") != "human":
                continue
            if created[n] < thr and (last.get(u["id"]) is None or last[u["id"]] < thr):
                viol4.append(n)
        detail["IAM-04-DORMANT"] = {"dormant_enabled": viol4}
        y4 = int(not viol4)

        # ---------------------------------------------------------------- IAM-05
        bg = [n for n, a in reg.items() if a["account_class"] == "break_glass" and not a["deleted"]]
        reg_file = REPO / realm / "registers" / "breakglass_accounts.json"
        registered = {r["username"] for r in json.loads(reg_file.read_text(encoding="utf-8"))["rows"]} if reg_file.exists() else set()
        v_i = [n for n in bg if n not in registered or ((users[n].get("attributes") or {}).get("account_type") or [None])[0] != "break_glass"]
        shadow = docker_exec("avoi-app-host", "getent shadow bgroot || true").strip()
        unlocked = bool(shadow) and not (shadow.split(":")[1].startswith(("!", "*")) or shadow.split(":")[1] == "")
        tickets = sor["ticket_system"]
        host_ticket = any(t["type"] == "emergency" and t["subject"] == "host:app-host:bgroot" and t["status"] == "open" for t in tickets)
        v_ii = unlocked and not host_ticket
        v_iii = []
        wfrom = t0 - params["event_window_days"] * DAY_MS
        for n in bg:
            for (et,) in conn.run("SELECT event_time FROM event_entity WHERE realm_id=:r AND user_id=:u AND type='LOGIN' "
                                  "AND event_time >= :f AND event_time < :t", r=realm_id, u=users[n]["id"], f=wfrom, t=t0):
                days_ago = (t0 - et) / DAY_MS
                covered = any(t["type"] == "emergency" and t["subject"] == f"account:{n}" and t["opened_days_ago"] >= days_ago
                              and (t["closed_days_ago"] is None or t["closed_days_ago"] <= days_ago) for t in tickets)
                if not covered:
                    v_iii.append(n)
        detail["IAM-05-BREAKGLASS"] = {"unregistered_or_unidentified": v_i, "host_unlocked_without_ticket": v_ii,
                                       "uncovered_bg_logins": sorted(set(v_iii))}
        y5 = int(not v_i and not v_ii and not v_iii)

        # ---------------------------------------------------------------- IAM-06
        rv = sor["review_system"]
        t_review = t0 - rv["days_ago"] * DAY_MS
        # reconstruct privileged membership at review time from the complete admin-event store
        uid2name = {u["id"]: n for n, u in users.items()}
        events = conn.run("SELECT admin_event_time, operation_type, resource_path, representation FROM admin_event_entity "
                          "WHERE realm_id=:r AND resource_type IN ('REALM_ROLE_MAPPING','GROUP_MEMBERSHIP') "
                          "AND admin_event_time < :t ORDER BY admin_event_time", r=realm_id, t=t0)
        state: dict[str, bool] = {}
        for et, op, path, rep in events:
            if et >= t_review:
                break
            parts = path.split("/")
            name = uid2name.get(parts[1]) if len(parts) > 1 else None
            if name is None:
                continue
            is_priv_rep = ("priv_admin" in (rep or "") or "ops_superuser" in (rep or "") or path.split("/")[2] == "groups")
            if is_priv_rep:
                state[name] = (op == "CREATE")
        priv_at_review = {n for n, v in state.items() if v}
        gaps = sorted(priv_at_review - set(rv["scope"]))
        unimpl = []
        for d in rv["decisions"]:
            if d["decision"] == "revoke" and d["username"] in priv_now:
                tracked = any(t["type"] == "access_exception" and t["subject"] == f"account:{d['username']}" and t["status"] == "open" for t in tickets)
                if not tracked:
                    unimpl.append(d["username"])
        current = rv["days_ago"] <= params["access_review_max_age_days"]
        detail["IAM-06-ACCESS-REVIEW"] = {"review_age_days": rv["days_ago"], "signed": rv["signed"], "scope_gaps": gaps,
                                          "untracked_unimplemented_revocations": unimpl, "priv_at_review": sorted(priv_at_review)}
        y6 = int(current and rv["signed"] and not gaps and not unimpl)
        # live login tests run LAST (after all event-store queries); their events are later than T0
        # ---------------------------------------------------------------- IAM-01
        clients = [c["clientId"] for c in kc.get(f"/{realm}/clients") if c.get("standardFlowEnabled") and c.get("publicClient")
                   and c["clientId"] in {"portal", "legacy-portal", "kiosk"}]
        in_scope = [n for n in sorted(priv_now) if users[n]["enabled"] and reg.get(n, {}).get("account_class") == "human"]
        bypass = []
        for n in in_scope:
            for c in clients:
                res = browser_login(realm, c, n, pw)
                if res.outcome == "authenticated":
                    bypass.append(f"{n}@{c}")
                elif res.outcome not in ("otp_challenged", "otp_enrolment_required"):
                    raise RuntimeError(f"oracle login test inconclusive {realm} {n}@{c}: {res.outcome} {res.detail}")
        detail["IAM-01-MFA-PRIV"] = {"in_scope": in_scope, "clients": clients, "bypass": bypass}
        y1 = int(not bypass)

    finally:
        conn.close()
    labels = {"IAM-01-MFA-PRIV": y1, "IAM-02-TERM-DISABLED": y2, "IAM-03-PRIV-AUTHZ": y3, "IAM-04-DORMANT": y4,
              "IAM-05-BREAKGLASS": y5, "IAM-06-ACCESS-REVIEW": y6}
    return {"labels": labels, "detail": detail}

