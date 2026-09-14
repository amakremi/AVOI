# Datasets

Provenance (source page, URL, DOI, licence, retrieval date, size, SHA-256, published checksum and verification status)
is recorded by `data/download_datasets.py` / `data/download_datasets.ps1` in `data/DATASET_MANIFEST.json` and `.csv`
(Table 1 is generated from it). The registry of authoritative sources is `data/manifests/dataset_sources.json`.

## Requirement-grounding sources (never used as label sources)

| Source | Use in this project |
|---|---|
| NIST OSCAL content v1.5.0 (usnistgov/oscal-content) | structured SP 800-53 Rev.5 catalogue/baselines reference |
| NIST SP 800-53A Rev.5 assessment procedures (CSV/XLSX, CSRC) | AC-02, AC-02(02), AC-02(03), AC-06(05), AC-06(07), IA-02(01), PS-04, AU-06 objectives and examine/interview/test methods (`data/processed/grounding/nist_800_53a_selected.csv`) |
| NIST RMF assessment cases (AC, IA families; historical SP 800-53A R1) | assessment-case activities informing evidence actions |
| NCA ECC-2:2024 (EN, AR) and NCA Guide to ECC Implementation | ECC clauses 1-9-5, 2-2-3-2 … 2-2-3-5, 2-2-4 used in objective references (`nca_ecc_2_2_excerpt.txt`, local only) |
| Secure Controls Framework 2026.2 (GitHub release) | IAC controls, Evidence Request List (E-IAM-01/03/07/08/09, E-HRS-12/19/29, E-MON-01/05) as evidence-action vocabulary; only identifiers are reproduced. SCF 2026.2 maps NCA **ECC-1:2018** (not ECC-2:2024); ECC-2:2024 clause numbers were read from the ECC document itself. |

## Layer A — controlled IAM assurance testbed (this project)

Docker Compose (Keycloak 26.3, PostgreSQL 16, busybox evidence repository, Alpine Linux host). 40 scenario families ×
8 scenarios = **320 live scenarios**, each assessed on **6 atomic objectives = 1,920 objective episodes**. Scenario
states are generated from the pre-declared distribution `config/scenario_generator.yaml`, applied to the live
system through the Keycloak admin API (grants, disables, deletions audited), real browser-flow logins with TOTP
enrolment, and time-shifting of the event stores to emulate organisational history. **Ground truth is computed by
`testbed/oracle.py` from the live configuration** (exhaustive login tests, complete event stores, host `/etc/shadow`,
systems of record) — never from generator parameters. 37 evidence actions (6–7 per objective), each executed by a
real collector with measured seconds, records and bytes. Violation prevalence per objective: 25–59%.
All 320 scenarios completed with 0 setup warnings and 0 failures (`data/processed/iam/collection_log.jsonl`).

These are **testbed** organisations; they are not real enterprises.

## Layer B — public telemetry replay (assurance micro-claims, NOT compliance labels)

### AIT Log Data Set V2.0 (Zenodo 10.5281/zenodo.5789064, CC BY-NC-SA 4.0)
*Subset (predefined, by archive size only):* testbeds **russellmitchell** (7.1 GB) and **santos** (10.0 GB); published
MD5 verified. *Evidence:* 10 log-source families indexed without labels (VPN, DNS/dnsmasq, Apache/Horde access, error
logs, auth.log, auditd, Suricata fast.log, mail, syslog/kern, metricbeat CPU). *Excluded as evidence:* attacker host
logs (`attacker_0`: attacks.log, dnsteal captures), user-simulation hosts, pcaps, binary journals.
*Episodes:* 576 ten-minute windows per testbed × 2 micro-claims = **2,304 episodes**.
*Micro-claims (defined from label TYPES after inspecting label temporal prevalence, before any method was run):*
`AIT-EXFIL` (no dnsteal/exfiltration-service labelled lines in the window; refuted in 848 windows) and
`AIT-INTRUSION` (no other attack-step labelled lines; refuted in only **12** windows → statistically weak).
*Split:* leave-one-testbed-out.

### CERT Insider Threat Test Dataset r4.2 (KiltHub 10.1184/R1/12841247.v1, CC BY 4.0)
*Release rationale:* r4.2 is the documented "dense needle" release (many instances per scenario, all channels) and
smaller than r5/r6. Published MD5s of `r4.2.tar.bz2` and `answers.tar.bz2` verified.
*Micro-claim:* `CERT-INSIDER` — no answer-key observable events of the user in the week.
*Sampling (seeded 20260914):* all insider user-weeks with answer-key events (326) + 2 clean active weeks per insider
(144) + 2 active weeks for each of 250 randomly selected non-insider users (499) = **969 episodes, 322 users**.
Case-control sampling inflates prevalence (33.6% refuted) relative to the population; prevalence-reweighted results
are in Table 9. *Evidence:* 10 generic, label-free channel statistics (after-hours logons, PC novelty, USB connects,
file events, HTTP volume, HTTP domain novelty, external e-mails, attachments, LDAP role change, psychometric N).
*Split:* StratifiedGroupKFold by user.

## Unavailable datasets (documented blockers)

| Dataset | Status | Reason |
|---|---|---|
| Splunk BOTS v3 | downloaded and checksum-verified (MD5 d7ccca99…), **not used** | the official questions/answers (the only ground truth) are released by e-mail request to bots@splunk.com; the data is in proprietary pre-indexed Splunk buckets requiring Splunk Enterprise and acceptance of its licence. Neither gate was bypassed. |
| LANL cyber1 | **not downloaded** | download links are issued only after submitting an e-mail/usage form (`csr.lanl.gov/data/cyber1/`). An automated submission with the user's e-mail was attempted once at the user's request and was blocked by the execution environment's safety policy; it was not retried or circumvented. The user can submit the form in a browser and place files in `data/raw/lanl/`. |

Consequently public replay covers **2 datasets** (AIT, CERT), below the "≥ 3 if feasible" target; the optional
random-effects meta-analysis (≥ 3 compatible public datasets) was not performed.
