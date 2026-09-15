# Stage-2 data independence

Stage 1 data (IAM scenarios `scn-*`, AIT testbeds russellmitchell/santos, CERT r4.2) are used in Stage 2 **only as
development data** (model fitting, calibrator selection). Adequacy validation, threshold tuning and confirmation use
data never used in Stage 1. Partition rules were fixed in `config/stage2.yaml` before any Stage-2 label was used.

| Domain | Development (Stage-1 data) | Adequacy validation + tuning (new) | Confirmation (new, disjoint) | Independence |
|---|---|---|---|---|
| Controlled IAM | 320 Stage-1 scenarios (1,920 episodes) | new scenario families 0–15 (128 scenarios, 768 episodes) | new families 16–39 (192 scenarios, 1,152 episodes) | **Independent**: 320 new live scenarios from the frozen generator with a new master seed (20261103; 0 seed collisions with Stage 1), same objectives, same distribution, ground truth from the live oracle |
| AIT-LDS v2.0 | russellmitchell, santos | testbed **fox** (720 windows × 2 claims) | testbeds **harrison**, **wardbeck** (1,440 windows × 2 claims) | **Independent testbeds** of the same official release (different simulated organisations/time periods); same attack-scenario family and generator → not an independent benchmark family |
| CERT | r4.2 (969 episodes) | 40% of sampled **r5.2** users (seeded split) | remaining 60% of r5.2 users | **Different official release** (independently generated organisation, adds scenario 4); same benchmark family/generator → external confirmation within the CERT family, not an independent benchmark |

## Selection rules (fixed before evaluation)
* **AIT:** the three smallest unused archives of the official AIT-LDS v2.0 Zenodo record (fox 15.8 GB, harrison 16.8 GB,
  wardbeck 17.2 GB), ordered by size only; smallest → validation. Not selected on any AVOI result.
* **CERT:** r5.2 is the only other release with per-scenario instance directories in the official answer key
  (dense release); r4.1, r5.1, r6.1 and r6.2 contain one instance per scenario. Episode sampling repeats the Stage-1 rule
  (all insider user-weeks with answer-key events + 2 clean active weeks per insider + 2 active weeks for 250 random
  non-insiders) with seed 20261103.
* **IAM:** 40 new families × 8 scenarios; family index < 16 → validation.

## Acquisition deviations and integrity
* **AIT by range requests.** Full archives (≈ 50 GB) were bandwidth-prohibitive. `data/ait_remote_subset.py` read the
  official ZIP central directory remotely and copied only `dataset.yaml`, `labels/*`, the evidence-family log files and
  every log file that has a label file (246 / 209 / 227 members; ≈ 0.3 GB each). Each member was CRC-32-verified against
  the official central directory; subset SHA-256 values are in `data/manifests/ait_stage2_subsets.json`. The published
  whole-archive MD5 could not be verified for these partial copies.
* **CERT r5.2:** full official archive; published MD5 verified (e24c1080…). Release harmonisation (decided from the
  official r5 readme and CSV headers only, before any Stage-2 label or model output was inspected; the r4.2 code path is
  unchanged): (i) r5 `email.csv` logs send/receive/view events → only `Send` events are kept, as in r4.2;
  (ii) r5 `attachments` lists attachment names and sizes instead of a count → the count of `;`-separated entries is used;
  (iii) r5 `file.csv` logs all file activity with `to_removable_media` flags, whereas r4.2 `file.csv` contains only copies
  to removable media → only rows with `to_removable_media = True` are counted; (iv) r5 `device.csv` adds `file_tree`
  and LDAP adds `projects` (both unused).
* **IAM:** the Stage-2 testbed run was interrupted by a host sleep (Docker Desktop stopped) after scenario 114; the runner
  recorded the failed attempts in `data/processed/iam_stage2/collection_log.jsonl` and scenarios without ground truth
  were regenerated from the same seeds after Docker restarted (no scenario was altered or skipped).
* During AIT indexing the importer prints per-label-type window counts (data summaries). No acquisition-policy or model
  result on Stage-2 data was inspected before the Stage-2 freeze.

## Limits of independence
All three domains reuse the Stage-1 evidence-action definitions, feature construction and generators; AIT and CERT
confirmation data come from the same benchmark families. Stage 2 therefore tests generalisation to new organisations /
testbeds / releases, not to unrelated datasets. BOTS v3 (downloaded, but its answer key is
e-mail gated and the data requires Splunk Enterprise) and LANL cyber1 (e-mail form gate) remain unusable; no gate was bypassed.
