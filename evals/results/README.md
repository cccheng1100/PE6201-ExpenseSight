# Evaluation Result Provenance

This directory contains only the results needed to explain or reproduce the
selected Dev checkpoints and final frozen Holdout evaluation. Earlier smoke
tests, mixed-prompt diagnostics, and superseded rules snapshots were moved to
the process archive outside the submission repository on 2026-10-04. They are
not evaluation benchmarks.

Resumable output files must include matching configuration and per-claim input
hashes in their metadata. Legacy outputs without that provenance are rejected
by the resume loader.

The historical `semantic-review-v1` Dev artifacts are:

- `model_outputs_dev_current-config.json`;
- `model_outputs_dev_current-config.metadata.json`;
- `hybrid_dev_current_config.json`.

They contain exactly 16 unique model outputs and 16 validated call records under
one configuration hash. The core Dev metrics are 1.0 warning recall, warning
precision, material-issue recall, evidence-reference validity, and appropriate
abstention, with zero false returns and zero unsupported or clean-case warnings.
These remain Dev results, not final holdout results.

The active prompt-frozen Dev artifacts are:

- `model_outputs_dev_semantic-review-v2.json`;
- `model_outputs_dev_semantic-review-v2.metadata.json`;
- `hybrid_dev_semantic-review-v2.json`.

They contain 16 unique validated outputs and 16 matching call records under
configuration hash `2cfb6311ed7f5f878c28d85416d906f57e37a7c0d21b0df9037f1810d9173fee`.
Core Dev results are 1.0 warning recall, material-issue recall,
evidence-reference validity, and appropriate abstention, with zero false
returns and zero clean-case warnings. Warning precision is 0.917 because
`DEV-011` received one additional hotel-location warning; this is retained as a
documented limitation rather than tuned away.

The final frozen Holdout artifacts are:

- `rules_only_holdout-v1.json`;
- `model_outputs_holdout-v1_semantic-review-v2.json`;
- `model_outputs_holdout-v1_semantic-review-v2.metadata.json`;
- `hybrid_holdout-v1_semantic-review-v2.json`.

They use the same `holdout-v1` component hashes and the frozen v2 configuration.
All 34 eligible model outputs have matching validated call records. The final
Hybrid result has zero false returns, 1.0 warning recall, 0.870 warning
precision, 0.133 clean-case warning rate, and 1.0 material-issue recall.
Interpretation and error analysis are in `docs/FINAL_EVALUATION.md`.
