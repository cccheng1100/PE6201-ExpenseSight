# Evaluation Harness

## Purpose

The harness tests whether ExpenseSight identifies annotated issues without
creating unsafe returns or excessive warnings on compliant claims. Unit tests
and evaluation serve different purposes: unit tests verify implementation
boundaries, while evaluation measures behaviour across complete claims.

## Compared configurations

Both configurations run on the same ordered dataset and policy version.

1. **Rules only** — deterministic rules and triage.
2. **Hybrid** — the same rules plus validated LLM review notes, warnings, and
   abstentions.

The LLM is advisory. Its output schema cannot express an automatic return.

## Reproducibility

Before a run, the harness verifies SHA-256 hashes for:

- model-visible claims;
- hidden ground truth;
- case manifest;
- policy.

If one component changes, the run stops until a new reviewed dataset version
is created. `holdout-v1` is the final frozen descriptor; `candidate-v1` remains
only the editable source snapshot.

Model-output resume has a separate provenance check. Each saved call records a
configuration hash covering the model, both prompt files, policy context,
warning taxonomy, output schema, and pipeline contract, plus a per-claim input
hash covering the visible claim and deterministic findings. Outputs without
matching provenance are not reused, even when they still pass structural
validation.

Offline Hybrid scoring enforces the same boundary. It requires the companion
metadata file, recomputes the active configuration and per-claim input hashes,
and re-runs the taxonomy contract validator before accepting saved outputs.
Replacing an output or mixing artifacts from another configuration therefore
causes evaluation to stop rather than silently producing a score.

## Matching policy

Warnings are not compared by prose. The primary issue match is:

```text
claim_id + warning_code + entity_ref
```

The harness separately checks whether all annotated material facts appear with
the same values. This produces `warning_fact_recall_diagnostic`. The split is
intentional: wording variation should not fail a match, but missing or
contradictory facts must remain visible.

## Metrics

- return precision, recall, reason recall, and false-return rate;
- warning precision and recall;
- unsupported-warning rate;
- clean-case warning rate;
- material-fact recall diagnostic;
- material-issue recall;
- evidence-reference validity;
- review-note recall diagnostic;
- appropriate abstention once expected abstentions are annotated.

In plain language, recall asks “how much of the expected problem set was
found?”, while precision asks “how much of the system output was supported?”.
False-return rate and clean-case warning rate measure harm to normal claims.
Evidence-reference validity checks traceability rather than correctness.
Appropriate abstention measures whether the system stops a named judgement when
its required evidence is unavailable; it does not treat abstention as a pass.

The clean-case warning rate directly tests the supplementary project question:
does a system designed to find problems create too many warnings on normal
claims?

## Honest limitations

- The final labels were reviewed by the project author, not multiple independent
  finance reviewers; inter-annotator agreement is therefore unavailable.
- The rules baseline cannot detect most cross-document semantic issues.
- Appropriate abstention is currently measured on three Dev tasks; this sample
  is useful for prompt iteration but too small for a final general claim.
- Hybrid results require paid API calls through OpenRouter. The generation script
  defaults to dry-run and requires explicit `--execute-live`; frozen Holdout
  runs additionally require `--allow-holdout`.
- Token usage and provider spend are recorded per call in the metadata file.
  List-price estimates are not the same as actual provider charges and must not
  be reported as spend.
- The selected Dev result is `hybrid_dev_semantic-review-v2.json`; its 16 model
  outputs and metadata share one configuration hash. Older v1 artifacts remain
  historical checkpoints only.
- The 50 cases are frozen as `holdout-v1`. Rules-only and final Hybrid results
  are complete; all 34 model-eligible calls passed output validation.
