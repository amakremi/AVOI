# Stage-2 failure cases (generated from confirmation traces and episode records)

AVOI at its validation-tuned threshold, raw (ungated) policy, confirmation partition, unless stated otherwise.

## Controlled IAM

### False assurances: 6 (terminal belief ≥ 0.95: 6; with conflicting evidence flag: 6)

By objective: {'IAM-05-BREAKGLASS': 4, 'IAM-01-MFA-PRIV': 1, 'IAM-06-ACCESS-REVIEW': 1}

- `s2scn-0207|IAM-01-MFA-PRIV` — true Y=0 — decision **Assured** after 1 acquisitions (stop: threshold; τ=0.9); initial belief 0.746; adequacy RESTRICTED
  - t=1: `kc_priv_user_credentials` → `all_priv_have_otp`; belief 0.998, Bayes risk 0.016
- `s2scn-0201|IAM-05-BREAKGLASS` — true Y=0 — decision **Assured** after 3 acquisitions (stop: threshold; τ=0.8); initial belief 0.429; adequacy RESTRICTED
  - t=1: `recon_register_vs_kc_attribute` → `consistent`; belief 0.732, Bayes risk 1.000
  - t=2: `kc_breakglass_login_events` → `no_bg_logins`; belief 0.918, Bayes risk 0.820
  - t=3: `host_local_emergency_account` → `locked`; belief 0.956, Bayes risk 0.439
- `s2scn-0213|IAM-05-BREAKGLASS` — true Y=0 — decision **Assured** after 3 acquisitions (stop: threshold; τ=0.8); initial belief 0.429; adequacy RESTRICTED
  - t=1: `recon_register_vs_kc_attribute` → `consistent`; belief 0.732, Bayes risk 1.000
  - t=2: `kc_breakglass_login_events` → `no_bg_logins`; belief 0.918, Bayes risk 0.820
  - t=3: `host_local_emergency_account` → `locked`; belief 0.956, Bayes risk 0.439
- `s2scn-0262|IAM-05-BREAKGLASS` — true Y=0 — decision **Assured** after 3 acquisitions (stop: threshold; τ=0.8); initial belief 0.429; adequacy RESTRICTED
  - t=1: `recon_register_vs_kc_attribute` → `consistent`; belief 0.732, Bayes risk 1.000
  - t=2: `kc_breakglass_login_events` → `no_bg_logins`; belief 0.918, Bayes risk 0.820
  - t=3: `host_local_emergency_account` → `locked`; belief 0.956, Bayes risk 0.439

### Harmful / misleading acquisitions: 91 episodes contain an acquisition moving P(Y=1|E) away from the true label by > 0.3

- `s2scn-0139|IAM-05-BREAKGLASS` — true Y=1 — decision **NotAssured** after 3 acquisitions (stop: threshold; τ=0.8); initial belief 0.429; adequacy RESTRICTED
  - t=1: `recon_register_vs_kc_attribute` → `consistent`; belief 0.732, Bayes risk 1.000
  - t=2: `kc_breakglass_login_events` → `no_bg_logins`; belief 0.918, Bayes risk 0.820
  - t=3: `host_local_emergency_account` → `unlocked`; belief 0.264, Bayes risk 0.529
- `s2scn-0217|IAM-05-BREAKGLASS` — true Y=1 — decision **NotAssured** after 3 acquisitions (stop: threshold; τ=0.8); initial belief 0.429; adequacy RESTRICTED
  - t=1: `recon_register_vs_kc_attribute` → `consistent`; belief 0.732, Bayes risk 1.000
  - t=2: `kc_breakglass_login_events` → `no_bg_logins`; belief 0.918, Bayes risk 0.820
  - t=3: `host_local_emergency_account` → `unlocked`; belief 0.264, Bayes risk 0.529
- `s2scn-0284|IAM-05-BREAKGLASS` — true Y=1 — decision **NotAssured** after 3 acquisitions (stop: threshold; τ=0.8); initial belief 0.429; adequacy RESTRICTED
  - t=1: `recon_register_vs_kc_attribute` → `consistent`; belief 0.732, Bayes risk 1.000
  - t=2: `kc_breakglass_login_events` → `no_bg_logins`; belief 0.918, Bayes risk 0.820
  - t=3: `host_local_emergency_account` → `unlocked`; belief 0.264, Bayes risk 0.529

### Escalations: 248 (Y=0: 90, Y=1: 158)

- `s2scn-0129|IAM-02-TERM-DISABLED` — true Y=1 — decision **HumanReview** after 1 acquisitions (stop: no_positive_value; τ=0.9); initial belief 0.744; adequacy VALIDATED
  - t=1: `recon_hr_vs_directory` → `unlinked_accounts_present`; belief 0.805, Bayes risk 1.000
- `s2scn-0136|IAM-02-TERM-DISABLED` — true Y=0 — decision **HumanReview** after 1 acquisitions (stop: no_positive_value; τ=0.9); initial belief 0.744; adequacy VALIDATED
  - t=1: `recon_hr_vs_directory` → `unlinked_accounts_present`; belief 0.805, Bayes risk 1.000

## AIT-LDS v2.0

### False assurances: 9 (terminal belief ≥ 0.95: 9; with conflicting evidence flag: 0)

By objective: {'AIT-INTRUSION': 9}

- `ait|harrison|1644303600|AIT-INTRUSION` — true Y=0 — decision **Assured** after 1 acquisitions (stop: threshold; τ=0.15); initial belief 0.982; adequacy RESTRICTED
  - t=1: `ait_query_web_error` → `no_data`; belief 0.988, Bayes risk 0.115
- `ait|harrison|1644307200|AIT-INTRUSION` — true Y=0 — decision **Assured** after 1 acquisitions (stop: threshold; τ=0.15); initial belief 0.982; adequacy RESTRICTED
  - t=1: `ait_query_web_error` → `no_data`; belief 0.988, Bayes risk 0.115
- `ait|harrison|1644307800|AIT-INTRUSION` — true Y=0 — decision **Assured** after 1 acquisitions (stop: threshold; τ=0.15); initial belief 0.982; adequacy RESTRICTED
  - t=1: `ait_query_web_error` → `no_data`; belief 0.988, Bayes risk 0.115
- `ait|harrison|1644308400|AIT-INTRUSION` — true Y=0 — decision **Assured** after 1 acquisitions (stop: threshold; τ=0.15); initial belief 0.982; adequacy RESTRICTED
  - t=1: `ait_query_web_error` → `no_data`; belief 0.988, Bayes risk 0.115

### Harmful / misleading acquisitions: 0 episodes contain an acquisition moving P(Y=1|E) away from the true label by > 0.3


### Escalations: 1465 (Y=0: 916, Y=1: 549)

- `ait|harrison|1643932800|AIT-EXFIL` — true Y=0 — decision **HumanReview** after 0 acquisitions (stop: no_positive_value; τ=0.5); initial belief 0.284; adequacy UNSUPPORTED
- `ait|harrison|1643933400|AIT-EXFIL` — true Y=0 — decision **HumanReview** after 0 acquisitions (stop: no_positive_value; τ=0.5); initial belief 0.284; adequacy UNSUPPORTED

## CERT (r4.2 dev / r5.2 confirmation)

### False assurances: 0 (terminal belief ≥ 0.95: 0; with conflicting evidence flag: 0)

None.


### Harmful / misleading acquisitions: 186 episodes contain an acquisition moving P(Y=1|E) away from the true label by > 0.3

- `cert|BYO1846|32|CERT-INSIDER` — true Y=1 — decision **HumanReview** after 1 acquisitions (stop: no_positive_value; τ=0.08); initial belief 0.662; adequacy RESTRICTED
  - t=1: `cert_device_connects` → `elevated`; belief 0.216, Bayes risk 0.431
- `cert|BYO1846|18|CERT-INSIDER` — true Y=1 — decision **HumanReview** after 1 acquisitions (stop: no_positive_value; τ=0.08); initial belief 0.662; adequacy RESTRICTED
  - t=1: `cert_device_connects` → `elevated`; belief 0.216, Bayes risk 0.431
- `cert|CHP1711|23|CERT-INSIDER` — true Y=1 — decision **HumanReview** after 1 acquisitions (stop: no_positive_value; τ=0.08); initial belief 0.662; adequacy RESTRICTED
  - t=1: `cert_device_connects` → `elevated`; belief 0.216, Bayes risk 0.431

### Escalations: 769 (Y=0: 351, Y=1: 418)

- `cert|ACM1770|62|CERT-INSIDER` — true Y=0 — decision **HumanReview** after 3 acquisitions (stop: no_positive_value; τ=0.08); initial belief 0.662; adequacy RESTRICTED
  - t=1: `cert_device_connects` → `no_data`; belief 0.971, Bayes risk 0.294
  - t=2: `cert_file_copies` → `no_data`; belief 0.985, Bayes risk 0.154
  - t=3: `cert_ldap_role_change` → `low`; belief 0.992, Bayes risk 0.081
- `cert|ACM1770|64|CERT-INSIDER` — true Y=0 — decision **HumanReview** after 3 acquisitions (stop: no_positive_value; τ=0.08); initial belief 0.662; adequacy RESTRICTED
  - t=1: `cert_device_connects` → `no_data`; belief 0.971, Bayes risk 0.294
  - t=2: `cert_file_copies` → `no_data`; belief 0.985, Bayes risk 0.154
  - t=3: `cert_ldap_role_change` → `low`; belief 0.992, Bayes risk 0.081

## Paired episode comparisons on VALIDATED IAM models

- AVOI vs B4-InformationGain: AVOI loss higher in 30 episodes, lower in 17; unsafe assurances AVOI 1 vs 1; episodes where AVOI acquired less AND incurred higher loss: 30
- AVOI vs B0-AllEvidence: AVOI loss higher in 70 episodes, lower in 48; unsafe assurances AVOI 1 vs 0; episodes where AVOI acquired less AND incurred higher loss: 70
- AVOI vs B3-CheapestFirst: AVOI loss higher in 30 episodes, lower in 20; unsafe assurances AVOI 1 vs 2; episodes where AVOI acquired less AND incurred higher loss: 30
- AVOI vs B2-Random[s0]: AVOI loss higher in 51 episodes, lower in 28; unsafe assurances AVOI 1 vs 0; episodes where AVOI acquired less AND incurred higher loss: 49

Per-objective UAR / loss / acquisitions (VALIDATED models):

| objective | method | UAR | expected loss | acquisitions |
|---|---|---|---|---|
| IAM-02-TERM-DISABLED | AVOI | 0.0000 | 0.188 | 1.00 |
| IAM-02-TERM-DISABLED | B0-AllEvidence | 0.0000 | 0.167 | 6.00 |
| IAM-02-TERM-DISABLED | B1-FixedChecklist | 0.0000 | 0.203 | 4.25 |
| IAM-02-TERM-DISABLED | B2-Random[s0] | 0.0000 | 0.167 | 3.62 |
| IAM-02-TERM-DISABLED | B3-CheapestFirst | 0.0000 | 0.214 | 4.60 |
| IAM-02-TERM-DISABLED | B4-InformationGain | 0.0000 | 0.167 | 1.87 |
| IAM-03-PRIV-AUTHZ | AVOI | 0.0000 | 0.745 | 2.49 |
| IAM-03-PRIV-AUTHZ | B0-AllEvidence | 0.0000 | 0.698 | 7.00 |
| IAM-03-PRIV-AUTHZ | B1-FixedChecklist | 0.0317 | 0.818 | 6.18 |
| IAM-03-PRIV-AUTHZ | B2-Random[s0] | 0.0000 | 0.708 | 6.09 |
| IAM-03-PRIV-AUTHZ | B3-CheapestFirst | 0.0159 | 0.750 | 6.66 |
| IAM-03-PRIV-AUTHZ | B4-InformationGain | 0.0000 | 0.745 | 4.80 |
| IAM-04-DORMANT | AVOI | 0.0000 | 0.250 | 1.00 |
| IAM-04-DORMANT | B0-AllEvidence | 0.0000 | 0.203 | 5.00 |
| IAM-04-DORMANT | B1-FixedChecklist | 0.0000 | 0.219 | 4.03 |
| IAM-04-DORMANT | B2-Random[s0] | 0.0000 | 0.208 | 2.74 |
| IAM-04-DORMANT | B3-CheapestFirst | 0.0000 | 0.193 | 4.80 |
| IAM-04-DORMANT | B4-InformationGain | 0.0000 | 0.250 | 1.00 |
| IAM-06-ACCESS-REVIEW | AVOI | 0.0096 | 0.578 | 1.33 |
| IAM-06-ACCESS-REVIEW | B0-AllEvidence | 0.0000 | 0.526 | 6.00 |
| IAM-06-ACCESS-REVIEW | B1-FixedChecklist | 0.0096 | 0.568 | 3.99 |
| IAM-06-ACCESS-REVIEW | B2-Random[s0] | 0.0000 | 0.500 | 4.79 |
| IAM-06-ACCESS-REVIEW | B3-CheapestFirst | 0.0096 | 0.578 | 4.99 |
| IAM-06-ACCESS-REVIEW | B4-InformationGain | 0.0096 | 0.531 | 2.45 |
