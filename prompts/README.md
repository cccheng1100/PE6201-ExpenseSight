# Prompts

`semantic_review_system.md` defines the stable role and safety boundary.
`semantic_review_request.md` is the per-claim request template.

The caller must enforce `evals/schemas/model_review_output.schema.json` as a
structured output format and then validate the parsed object with
`parse_model_review_output`. Prompt text alone is not a security boundary.

Prompt changes are developed against `data/dev/dev_claims.json`. The 50
candidate holdout labels must not be used to tune prompt wording.
