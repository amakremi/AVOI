"""Deterministic scenario-specification generator for the controlled IAM testbed.

generate_spec(scenario_index, cfg) is a pure function of (master_seed, scenario_index, cfg). It describes a
LEGITIMATE configuration state to be applied to Keycloak / evidence repository / Linux host. It does NOT produce
labels: ground truth is computed afterwards by testbed/oracle.py from the live system.

Time is expressed as days before the assessment reference time T0.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
FIRST = ["Aisha", "Omar", "Lina", "Fahad", "Sara", "Khalid", "Noura", "Yousef", "Maha", "Faisal", "Reem", "Majed",
         "Hind", "Turki", "Dana", "Saad", "Rana", "Nasser", "Joud", "Bandar", "Lama", "Hamad", "Amal", "Talal",
         "Mona", "Ziad", "Hala", "Rakan", "Nada", "Waleed"]
LAST = ["Alharbi", "Alqahtani", "Alghamdi", "Alzahrani", "Alotaibi", "Aldosari", "Alshehri", "Almutairi",
        "Alanazi", "Alshammari", "Alsubaie", "Alyami", "Alamri", "Alasmari", "Albalawi", "Aljohani"]
DEPTS = ["finance", "operations", "it", "hr", "sales", "engineering"]


def load_cfg() -> dict:
    return yaml.safe_load((ROOT / "config" / "scenario_generator.yaml").read_text(encoding="utf-8"))


def _rng(*keys) -> np.random.Generator:
    h = hashlib.sha256("|".join(map(str, keys)).encode()).digest()
    return np.random.default_rng(int.from_bytes(h[:8], "little"))


def family_latents(family_id: int, cfg: dict) -> dict:
    r = _rng(cfg["master_seed"], "family", family_id)
    fl = cfg["family_latents"]
    h = float(r.beta(*fl["hygiene_beta"]))
    m = float(np.clip(fl["doc_maturity_mix"] * h + (1 - fl["doc_maturity_mix"]) * r.beta(2, 2), 0, 1))
    return {"hygiene": h, "doc_maturity": m}


def generate_spec(scenario_index: int, cfg: dict | None = None) -> dict:
    cfg = cfg or load_cfg()
    spf = cfg["scenarios_per_family"]
    family_id = scenario_index // spf
    fam = family_latents(family_id, cfg)
    seed = int.from_bytes(hashlib.sha256(f"{cfg['master_seed']}|scenario|{scenario_index}".encode()).digest()[:8], "little")
    r = np.random.default_rng(seed)
    fl, mech, docs = cfg["family_latents"], cfg["mechanisms"], cfg["documents"]
    sd = fl["scenario_jitter_sd"]
    h = float(np.clip(fam["hygiene"] + r.normal(0, sd), 0.01, 0.99))
    m = float(np.clip(fam["doc_maturity"] + r.normal(0, sd), 0.01, 0.99))
    g = float(np.clip(1.6 - 1.2 * h, 0.2, 1.6))

    def p(base):
        return float(np.clip(base * g, 0.0, 0.95))

    def bern(prob):
        return bool(r.random() < prob)

    def ri(lo, hi):
        return int(r.integers(lo, hi + 1))

    sid = f"scn-{scenario_index:04d}"
    # ------------------------------------------------------------------ people and human accounts
    n_humans = ri(*fl["n_human_users"])
    used = set()
    persons, accounts = [], []
    for i in range(n_humans):
        while True:
            fn, ln = FIRST[r.integers(len(FIRST))], LAST[r.integers(len(LAST))]
            uname = f"{fn[0].lower()}.{ln.lower()}"
            if uname in used:
                uname = f"{uname}{ri(2, 99)}"
            if uname not in used:
                used.add(uname)
                break
        pid = f"P{scenario_index:04d}{i:03d}"
        persons.append({"person_id": pid, "employee_id": f"E{100000 + scenario_index * 100 + i}", "first": fn,
                        "last": ln, "email": f"{uname}@corp.test", "dept": DEPTS[r.integers(len(DEPTS))],
                        "status": "active", "term_days_ago": None})
        accounts.append({"username": uname, "account_class": "human", "person_id": pid, "enabled": True,
                         "deleted": False, "employee_id_attr": True, "account_type_attr": None,
                         "created_days_ago": None, "logins": [], "direct_roles": [], "groups": [],
                         "otp_required_action": False})
    acc = {a["username"]: a for a in accounts}
    per = {p_["person_id"]: p_ for p_ in persons}

    # ------------------------------------------------------------------ terminations (O2)
    tm = mech["termination"]
    n_term = int(r.choice(len(tm["n_terminations_probs"]), p=tm["n_terminations_probs"]))
    human_names = [a["username"] for a in accounts]
    order = list(r.permutation(human_names))
    terminated = order[:n_term]
    for u in terminated:
        a = acc[u]
        pr = per[a["person_id"]]
        pr["status"] = "terminated"
        pr["term_days_ago"] = ri(3, 180)
        if bern(p(tm["left_enabled_base"])):
            a["enabled"] = True
            a["term_left_enabled"] = True
        elif bern(tm["deleted_prob"]):
            a["deleted"] = True
            a["enabled"] = False
        else:
            a["enabled"] = False
    for a in accounts:
        if bern(p(tm["unlinked_account_base"])):
            a["employee_id_attr"] = False
    active_humans = [u for u in order[n_term:]]

    # ------------------------------------------------------------------ privileged membership (O3)
    pa = mech["privileged_authz"]
    n_priv = min(ri(*fl["n_privileged_humans"]), max(1, len(active_humans) - 3))
    priv_humans = active_humans[:n_priv]
    others = active_humans[n_priv:]
    grants, approvals = [], []   # grants: role/group assignments executed through the admin API (audited)

    def add_grant(user, path, days_ago):
        grants.append({"username": user, "path": path, "days_ago": days_ago})
        if path == "direct":
            acc[user]["direct_roles"].append("priv_admin")
        elif path == "group":
            acc[user]["groups"].append("Admins")
        elif path == "composite":
            acc[user]["direct_roles"].append("ops_superuser")

    for u in priv_humans:
        d = ri(100, 900)
        add_grant(u, "direct" if bern(0.5) else "group", d)
        approvals.append({"username": u, "approved_days_ago": d + ri(0, 5), "expires_in_days": ri(30, 700)})
    if priv_humans and bern(p(pa["expired_approval_base"])):
        approvals[int(r.integers(len(approvals)))]["expires_in_days"] = -ri(1, 200)
    if others and bern(pa["recent_legit_grant_prob"]):
        u = others.pop(0)
        d = ri(1, 60)
        add_grant(u, "direct" if bern(0.5) else "group", d)
        approvals.append({"username": u, "approved_days_ago": d + ri(0, 3), "expires_in_days": ri(90, 700)})
        priv_humans.append(u)
    unapproved = []
    for path, base in (("direct", pa["unapproved_direct_base"]), ("group", pa["unapproved_group_base"])):
        if others and bern(p(base)):
            u = others.pop(0)
            add_grant(u, path, ri(1, 400))
            unapproved.append(u)
    composite_exists = bern(pa["composite_role_prob"])
    if composite_exists and others:
        u = others.pop(0)
        d = ri(1, 600)
        add_grant(u, "composite", d)
        if bern(pa["unapproved_composite_base"] * g):
            unapproved.append(u)
        else:
            approvals.append({"username": u, "approved_days_ago": d + ri(0, 5), "expires_in_days": ri(30, 700)})
    register_present = bern(docs["doc_present_intercept"] + docs["doc_present_slope"] * m)
    register = {"present": register_present, "lag_days": ri(*pa["register_export_lag_days"]),
                "has_expiry_col": bern(pa["register_has_expiry_col_intercept"] + pa["register_has_expiry_col_slope"] * m)}

    # ------------------------------------------------------------------ service and break-glass accounts (O5)
    for i in range(ri(*fl["n_service_accounts"])):
        u = f"svc-app{i + 1}"
        accounts.append({"username": u, "account_class": "service", "person_id": None, "enabled": True,
                         "deleted": False, "employee_id_attr": False, "account_type_attr": "service",
                         "created_days_ago": ri(200, 1200), "logins": [], "direct_roles": [], "groups": [],
                         "otp_required_action": False})
    bgm = mech["breakglass"]
    bg_accounts = []
    for i in range(ri(*fl["n_breakglass_accounts"])):
        u = f"bg-admin-{i + 1}"
        a = {"username": u, "account_class": "break_glass", "person_id": None, "enabled": True, "deleted": False,
             "employee_id_attr": False, "account_type_attr": "break_glass", "created_days_ago": ri(200, 1500),
             "logins": [], "direct_roles": [], "groups": [], "otp_required_action": False,
             "registered": not bern(p(bgm["unregistered_base"]))}
        if bern(p(bgm["missing_attribute_base"])):
            a["account_type_attr"] = None
        accounts.append(a)
        bg_accounts.append(u)
        grants.append({"username": u, "path": "direct", "days_ago": a["created_days_ago"] - 1})
        a["direct_roles"].append("priv_admin")
        approvals.append({"username": u, "approved_days_ago": a["created_days_ago"], "expires_in_days": 3650})
    acc = {a["username"]: a for a in accounts}
    tickets = []
    tid = [1000]

    def ticket(kind, subject, status, opened, closed=None):
        tid[0] += 1
        tickets.append({"ticket_id": f"{kind[:3].upper()}-{tid[0]}", "type": kind, "subject": subject,
                        "status": status, "opened_days_ago": opened, "closed_days_ago": closed})

    bg_register_absent = bern(bgm["register_absent_base"] * (1 - m))
    host_unlocked = bern(p(bgm["host_unlocked_base"]))
    host = {"bgroot_exists": not bern(0.08), "bgroot_locked": not host_unlocked}
    if host_unlocked and bern(bgm["host_unlocked_with_ticket_prob"]):
        ticket("emergency", "host:app-host:bgroot", "open", ri(0, 5))
    for u in bg_accounts:
        if bern(p(bgm["bg_login_without_ticket_base"])):
            acc[u]["logins"].append({"days_ago": ri(1, 85), "client": "portal"})
        if bern(bgm["bg_login_with_ticket_prob"]):
            d = ri(1, 85)
            acc[u]["logins"].append({"days_ago": d, "client": "portal"})
            ticket("emergency", f"account:{u}", "closed", d + 1, max(0, d - 1))

    # ------------------------------------------------------------------ MFA configuration (O1)
    mm = mech["mfa"]
    u_ = r.random()
    if u_ < p(mm["flow_disabled_base"]):
        flow_mode = "disabled"
    elif u_ < p(mm["flow_disabled_base"]) + p(mm["flow_wrong_role_base"]):
        flow_mode = "wrong_role"
    else:
        flow_mode = "role_required"
    clients = [{"clientId": "portal", "override": None}]
    if bern(mm["legacy_client_prob"]):
        clients.append({"clientId": "legacy-portal", "override": "nonotp" if bern(p(mm["legacy_override_nonotp_base"])) else None})
    if bern(mm["kiosk_client_prob"]):
        clients.append({"clientId": "kiosk", "override": "benign_otp"})
    nondefault = [c["clientId"] for c in clients if c["clientId"] != "portal"]

    # ------------------------------------------------------------------ login history / dormancy (O4)
    dm = mech["dormancy"]
    for a in accounts:
        if a["account_class"] != "human":
            continue
        pr = per[a["person_id"]]
        a["created_days_ago"] = ri(120, 900) if bern(dm["old_account_prob"]) else ri(10, 85)
        if pr["status"] == "terminated":
            last_possible = pr["term_days_ago"]
            if a.get("term_left_enabled") and bern(tm["post_termination_login_prob"]):
                a["logins"].append({"days_ago": ri(0, max(0, last_possible - 1)), "client": "portal", "post_termination": True})
            if last_possible + 1 < a["created_days_ago"]:
                a["logins"].append({"days_ago": ri(last_possible + 1, min(a["created_days_ago"] - 1, last_possible + 60)), "client": "portal"})
            continue
        dormant = a["created_days_ago"] > 90 and bern(p(dm["dormant_account_base"]))
        if dormant:
            a["dormant_by_design"] = True
            if bern(0.5) and a["created_days_ago"] > 100:
                a["logins"].append({"days_ago": ri(95, min(a["created_days_ago"] - 1, 400)), "client": "portal"})
            if bern(dm["dormant_disabled_prob"]):
                a["enabled"] = False
            continue
        is_priv = a["username"] in priv_humans or a["username"] in unapproved
        for _ in range(ri(*dm["logins_per_active_user"])):
            client = "portal"
            if is_priv and nondefault and bern(mm["priv_uses_nondefault_client_prob"]):
                client = nondefault[int(r.integers(len(nondefault)))]
            elif nondefault and bern(0.2):
                client = nondefault[int(r.integers(len(nondefault)))]
            a["logins"].append({"days_ago": ri(0, min(80, a["created_days_ago"] - 1)), "client": client})
        if is_priv and flow_mode != "role_required" and bern(mm["voluntary_otp_enrolment_prob"]):
            a["otp_required_action"] = True
    for a in accounts:
        a["logins"].sort(key=lambda x: -x["days_ago"])  # chronological (oldest first)

    # ------------------------------------------------------------------ access review (O6)
    ar = mech["access_review"]
    current = bern(ar["current_review_intercept"] + ar["current_review_slope"] * h)
    review_days_ago = ri(5, 85) if current else ri(100, 320)
    removals = []
    if bern(ar["unrelated_removal_prob"]) and others:
        u = others.pop(0)
        d = ri(150, 400)
        add_grant(u, "direct", d)
        removals.append({"username": u, "days_ago": ri(1, d - 1)})
    removed_before_review = {x["username"] for x in removals if x["days_ago"] > review_days_ago}
    priv_at_review = sorted({gr["username"] for gr in grants
                             if gr["days_ago"] > review_days_ago and gr["username"] not in removed_before_review})
    scope = list(priv_at_review)
    if scope and bern(p(ar["scope_gap_base"])):
        scope.remove(scope[int(r.integers(len(scope)))])
    n_rev = int(r.choice(len(ar["n_revocations_probs"]), p=ar["n_revocations_probs"]))
    revocable = [u for u in scope if acc[u]["account_class"] == "human"]
    decisions = []
    for u in list(r.permutation(revocable))[:n_rev]:
        implemented = not bern(p(ar["unimplemented_revocation_base"]))
        decisions.append({"username": str(u), "decision": "revoke", "implemented": implemented})
        if implemented:
            removals.append({"username": str(u), "days_ago": max(0, review_days_ago - ri(1, 5))})
        elif bern(ar["exception_ticket_given_unimplemented"]):
            ticket("access_exception", f"account:{u}", "open", max(0, review_days_ago - 1))
    for u in scope:
        if u not in [d_["username"] for d_ in decisions]:
            decisions.append({"username": u, "decision": "keep", "implemented": True})
    review ={"days_ago": review_days_ago, "signed": bern(ar["signed_intercept"] + ar["signed_slope"] * m),
              "scope": scope, "decisions": decisions}
    # a user whose grant was removed no longer holds it
    removed_users = {x["username"] for x in removals}
    for u in removed_users:
        acc[u]["direct_roles"] = [x for x in acc[u]["direct_roles"] if x not in ("priv_admin", "ops_superuser")]
        acc[u]["groups"] = [x for x in acc[u]["groups"] if x != "Admins"]

    # ------------------------------------------------------------------ offboarding tickets
    ticket_system = bern(docs["ticket_system_intercept"] + docs["ticket_system_slope"] * m)
    for u in terminated:
        a, pr = acc[u], per[acc[u]["person_id"]]
        if a["enabled"]:
            x = r.random()
            if x < docs["ticket_closed_given_enabled"]:
                ticket("offboarding", pr["employee_id"], "closed", pr["term_days_ago"], max(0, pr["term_days_ago"] - 1))
            elif x < docs["ticket_closed_given_enabled"] + docs["ticket_open_given_enabled"]:
                ticket("offboarding", pr["employee_id"], "open", pr["term_days_ago"])
        elif bern(docs["ticket_closed_given_disabled"]):
            ticket("offboarding", pr["employee_id"], "closed", pr["term_days_ago"], max(0, pr["term_days_ago"] - 1))
        else:
            ticket("offboarding", pr["employee_id"], "open", pr["term_days_ago"])

    # ------------------------------------------------------------------ documents
    def doc_present():
        return bern(docs["doc_present_intercept"] + docs["doc_present_slope"] * m)

    mfa_doc = "absent"
    if doc_present():
        mfa_doc = "mandates" if bern(docs["mfa_policy_mandates_given_present"]) else "no_clause"
    exc_reg_present = bern(docs["exception_register_intercept"] + docs["exception_register_slope"] * m)
    override_nonotp = any(c["override"] == "nonotp" for c in clients)
    exc_rows = []
    if exc_reg_present:
        if override_nonotp and bern(docs["exception_listed_given_override"]):
            exc_rows.append({"exception": "legacy-portal client uses standard browser flow", "approved_by": "CISO"})
        if bern(docs["spurious_exception_prob"]):
            exc_rows.append({"exception": "vendor support account uses hardware token", "approved_by": "IT manager"})
    documents = {
        "mfa_policy": mfa_doc,
        "mfa_exception_register": {"present": exc_reg_present, "rows": exc_rows},
        "offboarding_procedure": doc_present(),
        "priv_access_procedure": doc_present(),
        "lifecycle_standard": doc_present(),
        "breakglass_procedure": doc_present(),
        "access_review_policy": doc_present(),
        "bg_register_present": not bg_register_absent,
        "review_export_present": doc_present(),
        "ticket_system": ticket_system,
        "dormancy_report": {"present": bern(dm["report_exists_intercept"] + dm["report_exists_slope"] * m),
                            "lag_days": ri(*dm["report_lag_days"])},
        "siem_export": {"present": bern(dm["siem_export_intercept"] + dm["siem_export_slope"] * m),
                        "lag_days": ri(*dm["siem_lag_days"])},
    }
    return {
        "scenario_id": sid, "scenario_index": scenario_index, "family_id": family_id, "seed": seed,
        "latent": {"hygiene": h, "doc_maturity": m, "family_hygiene": fam["hygiene"], "family_doc_maturity": fam["doc_maturity"]},
        "persons": persons, "accounts": accounts, "grants": grants, "removals": removals,
        "approvals": approvals, "approval_register": register, "composite_role": composite_exists,
        "flow_mode": flow_mode, "clients": clients, "host": host, "tickets": tickets, "review": review,
        "documents": documents, "password": "Tb-" + hashlib.sha256(str(seed).encode()).hexdigest()[:12],
    }


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(generate_spec(int(sys.argv[1]) if len(sys.argv) > 1 else 0), indent=1)[:6000])
