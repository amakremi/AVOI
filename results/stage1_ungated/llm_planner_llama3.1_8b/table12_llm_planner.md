**Table 12. Secondary: LLM-only planner (B8) vs AVOI-GRC on a predefined subset**

| method | n | UAR | expected_loss | mean_acquisitions | coverage | normalized_cost | note |
|---|---|---|---|---|---|---|---|
| AVOI-GRC | 384 | 0.000 [0.000, 0.000] | 0.391 [0.331, 0.448] | 1.591 [1.500, 1.685] | 0.745 [0.701, 0.786] | 0.718 | IAM outer fold 0 only; model llama3.1:8b; invalid responses 0 |
| AVOI-GRC(value-stop,bayes) | 384 | 0.000 [0.000, 0.000] | 0.281 [0.224, 0.339] | 1.917 [1.810, 2.023] | 0.875 [0.841, 0.906] | 0.794 | IAM outer fold 0 only; model llama3.1:8b; invalid responses 0 |
| B8-LLMPlanner | 384 | 0.000 [0.000, 0.000] | 0.305 [0.247, 0.365] | 6.167 [6.099, 6.234] | 0.852 [0.815, 0.885] | 1.629 | IAM outer fold 0 only; model llama3.1:8b; invalid responses 0 |
