# Experiment stages

- **Stage 1:** Evaluated the ungated evidence-acquisition policy on the controlled IAM testbed and public AIT/CERT replays. Its frozen inputs and CSV outputs are retained under `results/stage1_ungated/`.
- **Stage 2:** Added an evidence-model adequacy condition and confirmation evaluation on new partitions. Stage 2 inputs and CSV outputs are under `results/stage2/`.
- **Stage 3:** Evaluated adaptive evidence selection and external-model adequacy. Stage 3 inputs and CSV outputs are under `results/stage3/`.

Stage 2 and Stage 3 use the frozen hypotheses and partition rules in `docs/STAGE2_HYPOTHESES.md`, `docs/STAGE2_DATA_INDEPENDENCE.md`, and `config/stage3.yaml`. Earlier data are treated as development data when they are reused in a later stage.
