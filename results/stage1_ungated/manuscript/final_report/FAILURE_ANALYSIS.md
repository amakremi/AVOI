> Stage 1 (original ungated experiment). Manuscript-facing copy: the method display name is AVOI (the historical label is retained only in the archived files); all numbers identical to the archived artefact.

# Failure analysis (generated from held-out traces and episode records)

All counts refer to AVOI at its inner-tuned threshold in the primary condition unless stated otherwise. Traces are reproduced verbatim from `results/traces/`.

## Controlled IAM testbed (Layer A)

### False assurances (7 of 1920 episodes; 741 violated)
By objective/claim: IAM-01-MFA-PRIV: 2, IAM-05-BREAKGLASS: 2, IAM-06-ACCESS-REVIEW: 2, IAM-03-PRIV-AUTHZ: 1
Over-confident false assurances (terminal belief ≥ 0.95): 2 — these are calibration/model failures rather than acquisition-order failures.
False assurances whose acquired evidence included documentary evidence nominally supporting satisfaction (evidence-source reliability failure pattern): 3

Representative traces:
- episode `scn-0038|IAM-01-MFA-PRIV` — true Y=0 — decision **Assured** after 3 acquisitions (stop: threshold; tuned τ=0.5); initial belief 0.730
  - t=1: `kc_priv_user_credentials` → `some_priv_without_otp`; belief 0.276, risk 0.553 (top candidates: kc_priv_user_credentials AVOI=0.696; kc_realm_browser_flow AVOI=0.501)
  - t=2: `kc_realm_browser_flow` → `otp_enforced_priv_role`; belief 0.689, risk 1.000 (top candidates: kc_realm_browser_flow AVOI=0.128; action#4 AVOI=0.088)
  - t=3: `doc_mfa_exception_register` → `no_exceptions`; belief 0.969, risk 0.307 (top candidates: doc_mfa_exception_register AVOI=0.296; action#3 AVOI=0.181)
- episode `scn-0312|IAM-01-MFA-PRIV` — true Y=0 — decision **Assured** after 1 acquisitions (stop: threshold; tuned τ=0.4); initial belief 0.749
  - t=1: `kc_priv_user_credentials` → `all_priv_have_otp`; belief 0.994, risk 0.059 (top candidates: kc_priv_user_credentials AVOI=0.726; kc_realm_browser_flow AVOI=0.386)
- episode `scn-0076|IAM-03-PRIV-AUTHZ` — true Y=0 — decision **Assured** after 1 acquisitions (stop: threshold; tuned τ=0.8); initial belief 0.677
  - t=1: `recon_effective_vs_approvals` → `all_effective_approved`; belief 0.948, risk 0.523 (top candidates: recon_effective_vs_approvals AVOI=0.086; action#0 AVOI=-0.005)

### False non-assurances (101 episodes)
- episode `scn-0047|IAM-01-MFA-PRIV` — true Y=1 — decision **NotAssured** after 4 acquisitions (stop: threshold; tuned τ=0.4); initial belief 0.718
  - t=1: `kc_priv_user_credentials` → `some_priv_without_otp`; belief 0.215, risk 0.430 (top candidates: kc_priv_user_credentials AVOI=0.764; kc_realm_browser_flow AVOI=0.309)
  - t=2: `kc_realm_browser_flow` → `otp_enforced_priv_role`; belief 0.541, risk 1.000 (top candidates: kc_realm_browser_flow AVOI=0.009; doc_mfa_exception_register AVOI=-0.004)
  - t=3: `kc_client_flow_overrides` → `overrides_present`; belief 0.260, risk 0.519 (top candidates: kc_client_flow_overrides AVOI=0.538; action#6 AVOI=0.240)
  - t=4: `doc_mfa_exception_register` → `exceptions_listed`; belief 0.122, risk 0.243 (top candidates: doc_mfa_exception_register AVOI=0.062; action#0 AVOI=-0.004)
- episode `scn-0196|IAM-01-MFA-PRIV` — true Y=1 — decision **NotAssured** after 4 acquisitions (stop: threshold; tuned τ=0.4); initial belief 0.718
  - t=1: `kc_priv_user_credentials` → `some_priv_without_otp`; belief 0.215, risk 0.430 (top candidates: kc_priv_user_credentials AVOI=0.764; kc_realm_browser_flow AVOI=0.309)
  - t=2: `kc_realm_browser_flow` → `otp_enforced_priv_role`; belief 0.541, risk 1.000 (top candidates: kc_realm_browser_flow AVOI=0.009; doc_mfa_exception_register AVOI=-0.004)
  - t=3: `kc_client_flow_overrides` → `overrides_present`; belief 0.260, risk 0.519 (top candidates: kc_client_flow_overrides AVOI=0.538; action#6 AVOI=0.240)
  - t=4: `doc_mfa_exception_register` → `not_found`; belief 0.176, risk 0.352 (top candidates: doc_mfa_exception_register AVOI=0.062; action#0 AVOI=-0.004)

### Escalations: 459 HumanReview decisions; 62 were unnecessary in the sense that the complete available evidence would have supported a correct autonomous decision under the same threshold (AVOI stopped because the expected value of the remaining evidence did not exceed its cost/privacy/delay terms).
- episode `scn-0218|IAM-01-MFA-PRIV` — true Y=1 — decision **HumanReview** after 5 acquisitions (stop: no_positive_value; tuned τ=0.5); initial belief 0.730
  - t=1: `kc_priv_user_credentials` → `some_priv_without_otp`; belief 0.276, risk 0.553 (top candidates: kc_priv_user_credentials AVOI=0.696; kc_realm_browser_flow AVOI=0.501)
  - t=2: `kc_realm_browser_flow` → `otp_enforced_priv_role`; belief 0.689, risk 1.000 (top candidates: kc_realm_browser_flow AVOI=0.128; action#4 AVOI=0.088)
  - t=3: `doc_mfa_exception_register` → `not_found`; belief 0.572, risk 1.000 (top candidates: doc_mfa_exception_register AVOI=0.296; kc_client_flow_overrides AVOI=0.181)
  - t=4: `kc_client_flow_overrides` → `no_overrides`; belief 0.938, risk 0.622 (top candidates: kc_client_flow_overrides AVOI=0.180; doc_mfa_policy AVOI=0.025)
  - t=5: `doc_mfa_policy` → `mandates_priv_mfa`; belief 0.948, risk 0.519 (top candidates: doc_mfa_policy AVOI=0.031; action#4 AVOI=-0.036)
- episode `scn-0288|IAM-01-MFA-PRIV` — true Y=0 — decision **HumanReview** after 4 acquisitions (stop: no_positive_value; tuned τ=0.5); initial belief 0.730
  - t=1: `kc_priv_user_credentials` → `some_priv_without_otp`; belief 0.276, risk 0.553 (top candidates: kc_priv_user_credentials AVOI=0.696; kc_realm_browser_flow AVOI=0.501)
  - t=2: `kc_realm_browser_flow` → `otp_enforced_priv_role`; belief 0.689, risk 1.000 (top candidates: kc_realm_browser_flow AVOI=0.128; action#4 AVOI=0.088)
  - t=3: `doc_mfa_exception_register` → `exceptions_listed`; belief 0.382, risk 0.764 (top candidates: doc_mfa_exception_register AVOI=0.296; kc_client_flow_overrides AVOI=0.181)
  - t=4: `kc_client_flow_overrides` → `overrides_present`; belief 0.264, risk 0.527 (top candidates: kc_client_flow_overrides AVOI=0.130; action#6 AVOI=0.048)

### Most expensive acquisition sequences (top 1%: 19 episodes)
- episode `scn-0143|IAM-06-ACCESS-REVIEW` — true Y=1 — decision **Assured** after 3 acquisitions (stop: threshold; tuned τ=0.7); initial belief 0.422
  - t=1: `access_review_record` → `current_signed`; belief 0.806, risk 1.000 (top candidates: access_review_record AVOI=0.202; recon_revocations_vs_directory AVOI=-0.006)
  - t=2: `recon_revocations_vs_directory` → `all_revocations_implemented`; belief 0.889, risk 1.000 (top candidates: recon_revocations_vs_directory AVOI=0.008; action#0 AVOI=-0.008)
  - t=3: `recon_review_scope_vs_effective` → `scope_complete`; belief 0.944, risk 0.558 (top candidates: recon_review_scope_vs_effective AVOI=0.233; action#4 AVOI=0.081) — cost 2.587
- episode `scn-0234|IAM-06-ACCESS-REVIEW` — true Y=1 — decision **Assured** after 3 acquisitions (stop: threshold; tuned τ=0.7); initial belief 0.403
  - t=1: `access_review_record` → `current_signed`; belief 0.763, risk 1.000 (top candidates: access_review_record AVOI=0.170; recon_review_scope_vs_effective AVOI=-0.008)
  - t=2: `recon_revocations_vs_directory` → `all_revocations_implemented`; belief 0.892, risk 1.000 (top candidates: recon_revocations_vs_directory AVOI=0.019; action#0 AVOI=-0.009)
  - t=3: `recon_review_scope_vs_effective` → `scope_complete`; belief 0.956, risk 0.437 (top candidates: recon_review_scope_vs_effective AVOI=0.322; action#0 AVOI=0.022) — cost 2.422
- episode `scn-0129|IAM-06-ACCESS-REVIEW` — true Y=1 — decision **Assured** after 3 acquisitions (stop: threshold; tuned τ=0.7); initial belief 0.388
  - t=1: `access_review_record` → `current_signed`; belief 0.784, risk 1.000 (top candidates: access_review_record AVOI=0.173; action#0 AVOI=-0.009)
  - t=2: `recon_revocations_vs_directory` → `all_revocations_implemented`; belief 0.923, risk 0.772 (top candidates: recon_revocations_vs_directory AVOI=0.136; action#0 AVOI=-0.009)
  - t=3: `recon_review_scope_vs_effective` → `scope_complete`; belief 0.959, risk 0.408 (top candidates: recon_review_scope_vs_effective AVOI=0.135; action#4 AVOI=-0.003) — cost 2.392

### Episodes where B4-InformationGain beat AVOI on realised loss: 76 (AVOI better: 24; ties: 1820)
- episode `scn-0218|IAM-01-MFA-PRIV` — true Y=1 — decision **HumanReview** after 5 acquisitions (stop: no_positive_value; tuned τ=0.5); initial belief 0.730
  - t=1: `kc_priv_user_credentials` → `some_priv_without_otp`; belief 0.276, risk 0.553 (top candidates: kc_priv_user_credentials AVOI=0.696; kc_realm_browser_flow AVOI=0.501)
  - t=2: `kc_realm_browser_flow` → `otp_enforced_priv_role`; belief 0.689, risk 1.000 (top candidates: kc_realm_browser_flow AVOI=0.128; action#4 AVOI=0.088)
  - t=3: `doc_mfa_exception_register` → `not_found`; belief 0.572, risk 1.000 (top candidates: doc_mfa_exception_register AVOI=0.296; kc_client_flow_overrides AVOI=0.181)
  - t=4: `kc_client_flow_overrides` → `no_overrides`; belief 0.938, risk 0.622 (top candidates: kc_client_flow_overrides AVOI=0.180; doc_mfa_policy AVOI=0.025)
  - t=5: `doc_mfa_policy` → `mandates_priv_mfa`; belief 0.948, risk 0.519 (top candidates: doc_mfa_policy AVOI=0.031; action#4 AVOI=-0.036)
- episode `scn-0016|IAM-01-MFA-PRIV` — true Y=1 — decision **HumanReview** after 4 acquisitions (stop: no_positive_value; tuned τ=0.1); initial belief 0.730
  - t=1: `kc_priv_user_credentials` → `some_priv_without_otp`; belief 0.276, risk 0.552 (top candidates: kc_priv_user_credentials AVOI=0.697; kc_realm_browser_flow AVOI=0.463)
  - t=2: `kc_realm_browser_flow` → `otp_enforced_priv_role`; belief 0.672, risk 1.000 (top candidates: kc_realm_browser_flow AVOI=0.118; test_mfa_login_sample AVOI=0.078)
  - t=3: `kc_client_flow_overrides` → `no_overrides`; belief 0.941, risk 0.591 (top candidates: kc_client_flow_overrides AVOI=0.115; action#1 AVOI=-0.004)
  - t=4: `test_mfa_login_sample` → `all_challenged`; belief 0.963, risk 0.373 (top candidates: test_mfa_login_sample AVOI=0.167; action#1 AVOI=-0.004)
Decision patterns in these episodes (AVOI → B4-InformationGain): Assured→NotAssured: 1, HumanReview→Assured: 22, HumanReview→NotAssured: 41, NotAssured→HumanReview: 12

### Episodes where B5-GenericVOI beat AVOI on realised loss: 316 (AVOI better: 241; ties: 1363)
- episode `scn-0246|IAM-01-MFA-PRIV` — true Y=1 — decision **HumanReview** after 4 acquisitions (stop: no_positive_value; tuned τ=0.4); initial belief 0.726
  - t=1: `kc_priv_user_credentials` → `some_priv_without_otp`; belief 0.273, risk 0.547 (top candidates: kc_priv_user_credentials AVOI=0.696; kc_realm_browser_flow AVOI=0.347)
  - t=2: `kc_realm_browser_flow` → `otp_enforced_priv_role`; belief 0.626, risk 1.000 (top candidates: kc_realm_browser_flow AVOI=0.087; action#4 AVOI=0.046)
  - t=3: `kc_client_flow_overrides` → `overrides_present`; belief 0.472, risk 0.943 (top candidates: kc_client_flow_overrides AVOI=0.224; doc_mfa_exception_register AVOI=0.087)
  - t=4: `doc_mfa_exception_register` → `no_exceptions`; belief 0.837, risk 1.000 (top candidates: doc_mfa_exception_register AVOI=0.184; action#0 AVOI=0.086)
- episode `scn-0257|IAM-01-MFA-PRIV` — true Y=1 — decision **HumanReview** after 4 acquisitions (stop: no_positive_value; tuned τ=0.4); initial belief 0.726
  - t=1: `kc_priv_user_credentials` → `some_priv_without_otp`; belief 0.273, risk 0.547 (top candidates: kc_priv_user_credentials AVOI=0.696; kc_realm_browser_flow AVOI=0.347)
  - t=2: `kc_realm_browser_flow` → `otp_enforced_priv_role`; belief 0.626, risk 1.000 (top candidates: kc_realm_browser_flow AVOI=0.087; action#4 AVOI=0.046)
  - t=3: `kc_client_flow_overrides` → `overrides_present`; belief 0.472, risk 0.943 (top candidates: kc_client_flow_overrides AVOI=0.224; doc_mfa_exception_register AVOI=0.087)
  - t=4: `doc_mfa_exception_register` → `exceptions_listed`; belief 0.208, risk 0.416 (top candidates: doc_mfa_exception_register AVOI=0.184; action#0 AVOI=0.086)
Decision patterns in these episodes (AVOI → B5-GenericVOI): Assured→NotAssured: 1, HumanReview→Assured: 221, HumanReview→NotAssured: 57, NotAssured→Assured: 37

### Calibration: full-evidence TAN posterior Brier 0.077, ECE 0.021, slope 1.07, intercept 0.02. A slope < 1 indicates over-confident posteriors, which directly causes threshold-based stopping to accept too early.

### Conditional-dependence modelling: TAN vs Naive Bayes (A8) realised loss — TAN worse in 78 episodes, NB worse in 198 episodes (mean loss TAN 0.381 vs NB 0.424).

### Distribution-shift failures (reliability of one source category degraded at evaluation, no retraining)
Loss under degradation vs cold-start loss on the SAME episodes (the source category may exist only for some objectives): reconciliation 1.061 vs 0.421 (Δ +0.639, n=1600), configuration_state 0.666 vs 0.178 (Δ +0.488, n=320), directory_state 0.472 vs 0.333 (Δ +0.139, n=1600), host_state 0.631 vs 0.497 (Δ +0.134, n=320), authentication_log 0.310 vs 0.241 (Δ +0.069, n=1280), register_record 0.469 vs 0.409 (Δ +0.060, n=1280), ticket_record 0.425 vs 0.423 (Δ +0.002, n=960), hr_record 0.153 vs 0.153 (Δ +0.000, n=320), technical_test 0.178 vs 0.178 (Δ +0.000, n=320), policy_document 0.380 vs 0.381 (Δ -0.001, n=1920), audit_log 0.658 vs 0.659 (Δ -0.002, n=640)
Negative Δ (degradation improving loss) indicates that the degraded source was misleading for the fitted model on held-out data (e.g. under cross-testbed shift), not that degradation is beneficial in general.

## AIT-LDS v2.0 replay (Layer B)

### False assurances (262 of 2304 episodes; 860 violated)
By objective/claim: AIT-EXFIL: 250, AIT-INTRUSION: 12
Over-confident false assurances (terminal belief ≥ 0.95): 262 — these are calibration/model failures rather than acquisition-order failures.

Representative traces:
- episode `ait|russellmitchell|1642723200|AIT-EXFIL` — true Y=0 — decision **Assured** after 1 acquisitions (stop: threshold; tuned τ=0.25); initial belief 0.424
  - t=1: `ait_query_ids` → `no_data`; belief 0.995, risk 0.051 (top candidates: ait_query_ids AVOI=0.358; action#1 AVOI=0.151)
- episode `ait|russellmitchell|1642724400|AIT-EXFIL` — true Y=0 — decision **Assured** after 1 acquisitions (stop: threshold; tuned τ=0.25); initial belief 0.424
  - t=1: `ait_query_ids` → `no_data`; belief 0.995, risk 0.051 (top candidates: ait_query_ids AVOI=0.358; action#1 AVOI=0.151)
- episode `ait|russellmitchell|1642725000|AIT-EXFIL` — true Y=0 — decision **Assured** after 1 acquisitions (stop: threshold; tuned τ=0.25); initial belief 0.424
  - t=1: `ait_query_ids` → `no_data`; belief 0.995, risk 0.051 (top candidates: ait_query_ids AVOI=0.358; action#1 AVOI=0.151)

### False non-assurances (244 episodes)
- episode `ait|santos|1642317600|AIT-EXFIL` — true Y=1 — decision **NotAssured** after 0 acquisitions (stop: threshold; tuned τ=1.0); initial belief 0.111
- episode `ait|santos|1642318200|AIT-EXFIL` — true Y=1 — decision **NotAssured** after 0 acquisitions (stop: threshold; tuned τ=1.0); initial belief 0.111

### Escalations: 294 HumanReview decisions; 7 were unnecessary in the sense that the complete available evidence would have supported a correct autonomous decision under the same threshold (AVOI stopped because the expected value of the remaining evidence did not exceed its cost/privacy/delay terms).
- episode `ait|russellmitchell|1642773600|AIT-EXFIL` — true Y=0 — decision **HumanReview** after 3 acquisitions (stop: no_positive_value; tuned τ=0.25); initial belief 0.424
  - t=1: `ait_query_ids` → `low`; belief 0.542, risk 1.000 (top candidates: ait_query_ids AVOI=0.358; action#1 AVOI=0.151)
  - t=2: `ait_query_syslog` → `elevated`; belief 0.670, risk 1.000 (top candidates: ait_query_syslog AVOI=0.138; action#7 AVOI=0.081)
  - t=3: `ait_query_web_error` → `no_data`; belief 0.672, risk 1.000 (top candidates: ait_query_web_error AVOI=0.001; action#0 AVOI=-0.005)
- episode `ait|russellmitchell|1642781400|AIT-EXFIL` — true Y=0 — decision **HumanReview** after 3 acquisitions (stop: no_positive_value; tuned τ=0.25); initial belief 0.424
  - t=1: `ait_query_ids` → `low`; belief 0.542, risk 1.000 (top candidates: ait_query_ids AVOI=0.358; action#1 AVOI=0.151)
  - t=2: `ait_query_syslog` → `low`; belief 0.313, risk 0.625 (top candidates: ait_query_syslog AVOI=0.138; action#7 AVOI=0.081)
  - t=3: `ait_query_vpn` → `no_data`; belief 0.267, risk 0.533 (top candidates: ait_query_vpn AVOI=0.008; action#3 AVOI=-0.001)

### Most expensive acquisition sequences (top 1%: 23 episodes)
- episode `ait|russellmitchell|1642918800|AIT-EXFIL` — true Y=0 — decision **HumanReview** after 3 acquisitions (stop: no_positive_value; tuned τ=0.25); initial belief 0.424
  - t=1: `ait_query_ids` → `low`; belief 0.542, risk 1.000 (top candidates: ait_query_ids AVOI=0.358; action#1 AVOI=0.151)
  - t=2: `ait_query_syslog` → `elevated`; belief 0.670, risk 1.000 (top candidates: ait_query_syslog AVOI=0.138; action#7 AVOI=0.081)
  - t=3: `ait_query_web_error` → `high`; belief 0.686, risk 1.000 (top candidates: ait_query_web_error AVOI=0.001; action#0 AVOI=-0.005) — cost 3.347
- episode `ait|russellmitchell|1643020200|AIT-EXFIL` — true Y=0 — decision **HumanReview** after 3 acquisitions (stop: no_positive_value; tuned τ=0.25); initial belief 0.424
  - t=1: `ait_query_ids` → `low`; belief 0.542, risk 1.000 (top candidates: ait_query_ids AVOI=0.358; action#1 AVOI=0.151)
  - t=2: `ait_query_syslog` → `high`; belief 0.729, risk 1.000 (top candidates: ait_query_syslog AVOI=0.138; action#7 AVOI=0.081)
  - t=3: `ait_query_audit` → `low`; belief 0.711, risk 1.000 (top candidates: ait_query_audit AVOI=0.018; action#3 AVOI=-0.002) — cost 0.835
- episode `ait|russellmitchell|1642846800|AIT-EXFIL` — true Y=0 — decision **HumanReview** after 3 acquisitions (stop: no_positive_value; tuned τ=0.25); initial belief 0.424
  - t=1: `ait_query_ids` → `low`; belief 0.542, risk 1.000 (top candidates: ait_query_ids AVOI=0.358; action#1 AVOI=0.151)
  - t=2: `ait_query_syslog` → `elevated`; belief 0.670, risk 1.000 (top candidates: ait_query_syslog AVOI=0.138; action#7 AVOI=0.081)
  - t=3: `ait_query_web_error` → `no_data`; belief 0.672, risk 1.000 (top candidates: ait_query_web_error AVOI=0.001; action#0 AVOI=-0.005) — cost 0.606

### Episodes where B4-InformationGain beat AVOI on realised loss: 5 (AVOI better: 4; ties: 2295)
- episode `ait|russellmitchell|1642773600|AIT-EXFIL` — true Y=0 — decision **HumanReview** after 3 acquisitions (stop: no_positive_value; tuned τ=0.25); initial belief 0.424
  - t=1: `ait_query_ids` → `low`; belief 0.542, risk 1.000 (top candidates: ait_query_ids AVOI=0.358; action#1 AVOI=0.151)
  - t=2: `ait_query_syslog` → `elevated`; belief 0.670, risk 1.000 (top candidates: ait_query_syslog AVOI=0.138; action#7 AVOI=0.081)
  - t=3: `ait_query_web_error` → `no_data`; belief 0.672, risk 1.000 (top candidates: ait_query_web_error AVOI=0.001; action#0 AVOI=-0.005)
- episode `ait|russellmitchell|1642781400|AIT-EXFIL` — true Y=0 — decision **HumanReview** after 3 acquisitions (stop: no_positive_value; tuned τ=0.25); initial belief 0.424
  - t=1: `ait_query_ids` → `low`; belief 0.542, risk 1.000 (top candidates: ait_query_ids AVOI=0.358; action#1 AVOI=0.151)
  - t=2: `ait_query_syslog` → `low`; belief 0.313, risk 0.625 (top candidates: ait_query_syslog AVOI=0.138; action#7 AVOI=0.081)
  - t=3: `ait_query_vpn` → `no_data`; belief 0.267, risk 0.533 (top candidates: ait_query_vpn AVOI=0.008; action#3 AVOI=-0.001)
Decision patterns in these episodes (AVOI → B4-InformationGain): HumanReview→NotAssured: 5

### Episodes where B5-GenericVOI beat AVOI on realised loss: 146 (AVOI better: 148; ties: 2010)
- episode `ait|russellmitchell|1642723800|AIT-EXFIL` — true Y=0 — decision **HumanReview** after 3 acquisitions (stop: no_positive_value; tuned τ=0.25); initial belief 0.424
  - t=1: `ait_query_ids` → `low`; belief 0.542, risk 1.000 (top candidates: ait_query_ids AVOI=0.358; action#1 AVOI=0.151)
  - t=2: `ait_query_syslog` → `low`; belief 0.313, risk 0.625 (top candidates: ait_query_syslog AVOI=0.138; action#7 AVOI=0.081)
  - t=3: `ait_query_vpn` → `no_data`; belief 0.267, risk 0.533 (top candidates: ait_query_vpn AVOI=0.008; action#3 AVOI=-0.001)
- episode `ait|russellmitchell|1642742400|AIT-EXFIL` — true Y=0 — decision **HumanReview** after 3 acquisitions (stop: no_positive_value; tuned τ=0.25); initial belief 0.424
  - t=1: `ait_query_ids` → `low`; belief 0.542, risk 1.000 (top candidates: ait_query_ids AVOI=0.358; action#1 AVOI=0.151)
  - t=2: `ait_query_syslog` → `low`; belief 0.313, risk 0.625 (top candidates: ait_query_syslog AVOI=0.138; action#7 AVOI=0.081)
  - t=3: `ait_query_vpn` → `no_data`; belief 0.267, risk 0.533 (top candidates: ait_query_vpn AVOI=0.008; action#3 AVOI=-0.001)
Decision patterns in these episodes (AVOI → B5-GenericVOI): HumanReview→Assured: 21, HumanReview→NotAssured: 125

### Calibration: full-evidence TAN posterior Brier 0.254, ECE 0.255, slope 0.19, intercept -0.19. A slope < 1 indicates over-confident posteriors, which directly causes threshold-based stopping to accept too early.

### Conditional-dependence modelling: TAN vs Naive Bayes (A8) realised loss — TAN worse in 12 episodes, NB worse in 6 episodes (mean loss TAN 1.477 vs NB 1.474).

### Distribution-shift failures (reliability of one source category degraded at evaluation, no retraining)
Loss under degradation vs cold-start loss on the SAME episodes (the source category may exist only for some objectives): audit_log 1.477 vs 1.477 (Δ +0.000, n=2304), authentication_log 1.477 vs 1.477 (Δ +0.000, n=2304), host_state 1.477 vs 1.477 (Δ +0.000, n=2304), system_log 1.476 vs 1.477 (Δ -0.001, n=2304), communication_record 1.475 vs 1.477 (Δ -0.001, n=2304), network_observation 1.061 vs 1.477 (Δ -0.415, n=2304)
Negative Δ (degradation improving loss) indicates that the degraded source was misleading for the fitted model on held-out data (e.g. under cross-testbed shift), not that degradation is beneficial in general.

## CERT r4.2 replay (Layer B)

### False assurances (10 of 969 episodes; 326 violated)
By objective/claim: CERT-INSIDER: 10
Over-confident false assurances (terminal belief ≥ 0.95): 10 — these are calibration/model failures rather than acquisition-order failures.

Representative traces:
- episode `cert|FBA0348|38|CERT-INSIDER` — true Y=0 — decision **Assured** after 1 acquisitions (stop: threshold; tuned τ=0.9); initial belief 0.657
  - t=1: `cert_device_connects` → `no_data`; belief 0.969, risk 0.314 (top candidates: cert_device_connects AVOI=0.488; cert_file_copies AVOI=0.208)
- episode `cert|FBA0348|68|CERT-INSIDER` — true Y=0 — decision **Assured** after 1 acquisitions (stop: threshold; tuned τ=0.9); initial belief 0.657
  - t=1: `cert_device_connects` → `no_data`; belief 0.969, risk 0.314 (top candidates: cert_device_connects AVOI=0.488; cert_file_copies AVOI=0.208)
- episode `cert|FAW0032|22|CERT-INSIDER` — true Y=0 — decision **Assured** after 1 acquisitions (stop: threshold; tuned τ=0.9); initial belief 0.684
  - t=1: `cert_device_connects` → `no_data`; belief 0.983, risk 0.169 (top candidates: cert_device_connects AVOI=0.545; cert_file_copies AVOI=0.280)

### False non-assurances (130 episodes)
- episode `cert|CCL0068|28|CERT-INSIDER` — true Y=1 — decision **NotAssured** after 1 acquisitions (stop: threshold; tuned τ=0.9); initial belief 0.657
  - t=1: `cert_device_connects` → `elevated`; belief 0.213, risk 0.426 (top candidates: cert_device_connects AVOI=0.488; action#3 AVOI=0.208)
- episode `cert|CCL0068|29|CERT-INSIDER` — true Y=1 — decision **NotAssured** after 1 acquisitions (stop: threshold; tuned τ=0.9); initial belief 0.657
  - t=1: `cert_device_connects` → `elevated`; belief 0.213, risk 0.426 (top candidates: cert_device_connects AVOI=0.488; action#3 AVOI=0.208)

### Escalations: 67 HumanReview decisions; 9 were unnecessary in the sense that the complete available evidence would have supported a correct autonomous decision under the same threshold (AVOI stopped because the expected value of the remaining evidence did not exceed its cost/privacy/delay terms).
- episode `cert|EHD0584|39|CERT-INSIDER` — true Y=0 — decision **HumanReview** after 3 acquisitions (stop: no_positive_value; tuned τ=0.8); initial belief 0.643
  - t=1: `cert_device_connects` → `low`; belief 0.439, risk 0.878 (top candidates: cert_device_connects AVOI=0.453; cert_file_copies AVOI=0.212)
  - t=2: `cert_file_copies` → `low`; belief 0.401, risk 0.802 (top candidates: cert_file_copies AVOI=0.042; cert_psychometric_neuroticism AVOI=0.030)
  - t=3: `cert_psychometric_neuroticism` → `low`; belief 0.412, risk 0.824 (top candidates: cert_psychometric_neuroticism AVOI=0.022; action#0 AVOI=-0.003)
- episode `cert|PAD0773|56|CERT-INSIDER` — true Y=1 — decision **HumanReview** after 2 acquisitions (stop: no_positive_value; tuned τ=0.8); initial belief 0.643
  - t=1: `cert_device_connects` → `low`; belief 0.439, risk 0.878 (top candidates: cert_device_connects AVOI=0.453; cert_file_copies AVOI=0.212)
  - t=2: `cert_file_copies` → `high`; belief 0.771, risk 1.000 (top candidates: cert_file_copies AVOI=0.042; action#9 AVOI=0.030)

### Most expensive acquisition sequences (top 1%: 9 episodes)
- episode `cert|BIS0247|48|CERT-INSIDER` — true Y=1 — decision **HumanReview** after 7 acquisitions (stop: no_positive_value; tuned τ=0.9); initial belief 0.684
  - t=1: `cert_device_connects` → `low`; belief 0.456, risk 0.912 (top candidates: cert_device_connects AVOI=0.545; cert_file_copies AVOI=0.280)
  - t=2: `cert_file_copies` → `elevated`; belief 0.518, risk 1.000 (top candidates: cert_file_copies AVOI=0.045; cert_email_attachments AVOI=-0.000)
  - t=3: `cert_ldap_role_change` → `low`; belief 0.556, risk 1.000 (top candidates: cert_ldap_role_change AVOI=0.079; cert_psychometric_neuroticism AVOI=0.029)
  - t=4: `cert_psychometric_neuroticism` → `high`; belief 0.609, risk 1.000 (top candidates: cert_psychometric_neuroticism AVOI=0.003; cert_email_attachments AVOI=-0.005)
  - t=5: `cert_email_attachments` → `low`; belief 0.491, risk 0.983 (top candidates: cert_email_attachments AVOI=0.008; cert_logon_afterhours AVOI=-0.007)
  - t=6: `cert_logon_afterhours` → `elevated`; belief 0.548, risk 1.000 (top candidates: cert_logon_afterhours AVOI=0.037; action#1 AVOI=0.014)
  - t=7: `cert_http_volume` → `low`; belief 0.597, risk 1.000 (top candidates: cert_http_volume AVOI=0.009; action#5 AVOI=0.003) — cost 0.271
- episode `cert|BSS0369|8|CERT-INSIDER` — true Y=1 — decision **NotAssured** after 1 acquisitions (stop: threshold; tuned τ=0.9); initial belief 0.676
  - t=1: `cert_device_connects` → `high`; belief 0.340, risk 0.680 (top candidates: cert_device_connects AVOI=0.460; action#3 AVOI=0.228) — cost 0.072
- episode `cert|BSS0369|38|CERT-INSIDER` — true Y=0 — decision **NotAssured** after 1 acquisitions (stop: threshold; tuned τ=0.9); initial belief 0.676
  - t=1: `cert_device_connects` → `high`; belief 0.340, risk 0.680 (top candidates: cert_device_connects AVOI=0.460; action#3 AVOI=0.228) — cost 0.070

### Episodes where B4-InformationGain beat AVOI on realised loss: 34 (AVOI better: 21; ties: 914)
- episode `cert|AHM0410|60|CERT-INSIDER` — true Y=1 — decision **NotAssured** after 1 acquisitions (stop: threshold; tuned τ=0.9); initial belief 0.657
  - t=1: `cert_device_connects` → `low`; belief 0.434, risk 0.868 (top candidates: cert_device_connects AVOI=0.488; cert_file_copies AVOI=0.208)
- episode `cert|AHM0410|16|CERT-INSIDER` — true Y=1 — decision **NotAssured** after 1 acquisitions (stop: threshold; tuned τ=0.9); initial belief 0.657
  - t=1: `cert_device_connects` → `low`; belief 0.434, risk 0.868 (top candidates: cert_device_connects AVOI=0.488; cert_file_copies AVOI=0.208)
Decision patterns in these episodes (AVOI → B4-InformationGain): HumanReview→Assured: 2, HumanReview→NotAssured: 20, NotAssured→Assured: 2, NotAssured→HumanReview: 10

### Episodes where B5-GenericVOI beat AVOI on realised loss: 54 (AVOI better: 43; ties: 872)
- episode `cert|AHM0410|60|CERT-INSIDER` — true Y=1 — decision **NotAssured** after 1 acquisitions (stop: threshold; tuned τ=0.9); initial belief 0.657
  - t=1: `cert_device_connects` → `low`; belief 0.434, risk 0.868 (top candidates: cert_device_connects AVOI=0.488; cert_file_copies AVOI=0.208)
- episode `cert|AHM0410|16|CERT-INSIDER` — true Y=1 — decision **NotAssured** after 1 acquisitions (stop: threshold; tuned τ=0.9); initial belief 0.657
  - t=1: `cert_device_connects` → `low`; belief 0.434, risk 0.868 (top candidates: cert_device_connects AVOI=0.488; cert_file_copies AVOI=0.208)
Decision patterns in these episodes (AVOI → B5-GenericVOI): HumanReview→Assured: 31, HumanReview→NotAssured: 5, NotAssured→Assured: 18

### Calibration: full-evidence TAN posterior Brier 0.105, ECE 0.031, slope 0.68, intercept -0.26. A slope < 1 indicates over-confident posteriors, which directly causes threshold-based stopping to accept too early.

### Conditional-dependence modelling: TAN vs Naive Bayes (A8) realised loss — TAN worse in 40 episodes, NB worse in 50 episodes (mean loss TAN 0.441 vs NB 0.451).

### Distribution-shift failures (reliability of one source category degraded at evaluation, no retraining)
Loss under degradation vs cold-start loss on the SAME episodes (the source category may exist only for some objectives): device_activity 1.315 vs 0.441 (Δ +0.874, n=969), file_activity 0.443 vs 0.441 (Δ +0.002, n=969), hr_record 0.442 vs 0.441 (Δ +0.001, n=969), communication_record 0.441 vs 0.441 (Δ +0.000, n=969), network_observation 0.441 vs 0.441 (Δ +0.000, n=969), authentication_log 0.440 vs 0.441 (Δ -0.001, n=969)
Negative Δ (degradation improving loss) indicates that the degraded source was misleading for the fitted model on held-out data (e.g. under cross-testbed shift), not that degradation is beneficial in general.
