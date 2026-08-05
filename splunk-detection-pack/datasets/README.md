# DanInTheWild Labeled Dataset

Ground-truth set for the "detect absence of refusal" Splunk rule (Week 4).

## Source
Extracted from a Garak `dan.DanInTheWild` run (256 real-world jailbreak
prompts) against `llama3.2:3b` via Ollama. See lab notebook Entry 7.

## Files
- `daninthewild_labeled.jsonl` — **canonical**. One record per line.
- `daninthewild_labeled.csv` — convenience only. Model outputs contain
  newlines; use a real CSV parser (quotes respected), not line-splitting.

## Schema
| field  | meaning |
|--------|---------|
| label  | `bypass` = refusal absent · `refusal` = refusal present |
| score  | Garak `mitigation.MitigationBypass` (1.0 bypass / 0.0 refusal) |
| prompt | the jailbreak prompt sent to the model |
| output | the model's response |

## Label semantics — read before using
Labels measure **whether the model refused**, not whether the output was
harmful. `bypass` means the guardrail did not fire; it does **not** mean the
response was dangerous. This is an absence-of-refusal signal, not a
harmful-vs-safe judgment.

## Counts
256 records: 167 bypass / 89 refusal (65.23% attack success rate).
