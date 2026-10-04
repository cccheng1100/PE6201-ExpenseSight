# High-Level Architecture

```text
Structured claim + independent attachment descriptions
                    |
                    v
          Input and arithmetic validation
                    |
                    v
          Deterministic policy rules
                    |
             +------+------+
             |             |
      confirmed fail    no confirmed fail
             |             |
             |      optional route facts
             |             |
             |      policy context + LLM
             |             |
             |      advisory output validator
             |             |
             v             v
RETURN_TO_EMPLOYEE     PROCEED_TO_HUMAN
       (LLM skipped)          |
                      Review Note / Warning /
                      task-scoped Abstention
                              |
                       Evidence brief
```

External intelligence is advisory. The validator prevents model or route-tool
output from creating an automatic return. A deterministic return short-circuits
the semantic review, so the LLM is not called and advisory outputs are not
mixed into a terminal employee action.

The triage guardrail also checks evidence provenance, reliability, plausible
exceptions, and employee actionability before a rule finding may become a
return reason. Neutral context is carried separately as `Review Note` output.

See `REVIEW_DECISION_POLICY.md` for the annotation and runtime boundary.

Expense lines and attachments are not assumed to be one-to-one. Each attachment
keeps a one-sentence OCR description plus links to relevant expense lines. This
allows duplicate uploads to be ignored without treating them as duplicate spend.
