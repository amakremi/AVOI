# Stage-2 hypotheses (S1–S4)

Written before the Stage-2 freeze (`results/stage2/EXPERIMENT_FREEZE_STAGE2.json`) and before any Stage-2 adequacy
validation or confirmation evaluation. **These are not part of the Stage-1 pre-registration.** They were formulated
after Stage-1 results were known (Stage-1 AIT results motivated the adequacy condition), so they are prospective only
relative to the Stage-2 frozen protocol and the new Stage-2 data. Stage-1 hypotheses H1–H5 and their outcomes are
unchanged (see `docs/PREREGISTERED_HYPOTHESES.md`, `results/stage1_ungated/final_report/RESULTS.md`).

Definitions: adequacy status per evidence model (objective / micro-claim) from `config/model_adequacy.yaml` on the
adequacy-validation partition; UAR = #(Assured ∧ Y=0)/#(Y=0); coverage = share of autonomous terminal decisions;
confirmation partition = new data never used for fitting, calibration, adequacy or tuning. α = 0.05, Holm within family.

**S1 — adequacy diagnosis.** Evidence-model adequacy diagnostics identify evidence models whose discrimination,
calibration or sample support is insufficient for autonomous AVOI use.
*Operationalisation:* descriptive. S1 is **supported** if the frozen policy yields at least one non-VALIDATED model
AND, on the confirmation partition, the ungated AVOI of non-VALIDATED models has a higher unsafe-assurance rate or
higher expected loss (group bootstrap CI of the difference to VALIDATED models' pooled rate excludes 0), i.e. the
diagnosis made on validation data is borne out on untouched data. **Not testable** if every model is VALIDATED or every
model fails. *Partially supported* if non-VALIDATED models exist but the confirmation difference is not significant.

**S2 — gate enforcement.** Enforcing evidence-model adequacy prevents autonomous terminal assurance in domains that
fail the predefined eligibility policy.
*Operationalisation:* on confirmation, enforced AVOI issues zero Assured and zero NotAssured decisions for every
non-VALIDATED model, each gated episode carries reason MODEL_ADEQUACY_RESTRICTED or MODEL_ADEQUACY_UNSUPPORTED, and
VALIDATED models are unaffected (enforced = raw). **Supported** iff all three hold.

**S3 — acquisition efficiency on validated models.** On VALIDATED models, AVOI retains its acquisition-efficiency
advantage relative to fixed (B1) and exhaustive (B0) evidence collection.
*Operationalisation:* confirmation episodes of VALIDATED models pooled per domain; paired Wilcoxon on per-episode
acquisitions (AVOI − comparator), Holm over the two comparators; group bootstrap CI of the mean difference.
**Supported** in a domain if both comparisons are significant with CI < 0; also reported: expected loss and UAR
differences (not part of the decision rule, never used to reinterpret S3).

**S4 — safety versus coverage.** The effect of adequacy enforcement on unsafe assurance is accompanied by an explicit
change in autonomous coverage.
*Operationalisation:* for every non-VALIDATED model, report ΔUAR (enforced − raw) with CI and Δcoverage; S4 is
**supported** if every non-zero ΔUAR co-occurs with Δcoverage < 0 and all reports present both quantities jointly
(checked by the report generator). **Not testable** if all models are VALIDATED.

Not hypotheses: Stage-2 replication of Stage-1 comparisons (information gain, generic VOI, confidence threshold,
all-evidence), asymmetric-loss ablation, missingness, privacy, budget, LLM planner — reported descriptively with paired
tests; they cannot upgrade Stage-1 H1/H2 outcomes.
