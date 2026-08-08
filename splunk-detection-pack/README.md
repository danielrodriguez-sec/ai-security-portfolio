# Splunk Detection Content Pack — LLM Application Abuse

Detection content for abuse of customer-facing LLM applications, built and
validated against a real labeled corpus (256 real-world jailbreak prompts,
Garak `dan.DanInTheWild` vs `llama3.2:3b`).

## Contents

| File | What it is |
|------|------------|
| `detect_absence_of_refusal.spl` | Deployable detection. Flags model responses that lack a lead-position refusal — candidate guardrail bypasses. Mapped to OWASP LLM01:2025 and MITRE ATLAS AML.T0054. |
| `EVALUATION.md` | Confusion matrices and precision/recall against audited ground truth, with the keyword-detector baseline and an honest note on the deployable rule's self-consistency check. |
| `../datasets/` | The labeled corpus, corrected labels, and the relabeling script. |
| `../findings/garak-mitigationbypass-coverage-gap.md` | The research finding this pack rests on: Garak's string detector misclassifies refusals in both directions, correcting reported ASR from 65.23% to 58.2%. |

## Key result

Against audited ground truth, a keyword refusal detector (Garak
`MitigationBypass`) scores **precision 0.725 / recall 0.812** — wrong in both
directions. It both raises false alarms on genuine refusals and misses genuine
bypasses. This is why absence-of-refusal detection cannot rest on keyword
matching alone, and why the corrected ground truth in `../datasets/` matters.

## Method note

- Ground truth is `label_corrected` (both-directions audited), not Garak's raw
  `MitigationBypass` output.
- Single-turn isolation throughout (fresh model context per probe).
- Frameworks: OWASP LLM Top 10 (2025), MITRE ATLAS v5.6.0.
