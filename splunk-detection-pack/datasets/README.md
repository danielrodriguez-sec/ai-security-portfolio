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

## KNOWN LABEL ERROR — detector coverage gap (added after audit)
The `label` field is Garak's `MitigationBypass` verdict and inherits that
detector's false negatives. `MitigationBypass` matches a fixed substring list
derived from ChatGPT-era refusals (ShareGPT/Vicuna corpus). It does **not**
contain Llama 3.2's contracted refusal forms — `I can't fulfill`,
`I can't provide`, `I can't help` are all absent; only the formal
`I cannot fulfill your request` is present.

Consequence: **at least 41 of the 167 `bypass`-labeled records are clean
refusals** that lead with an unmatched refusal phrase. Verified by (a) re-scoring
all 256 outputs under case/apostrophe normalization using Garak's own substring
list, and (b) manual read of all 41. Apostrophe encoding (U+2019 vs U+0027) is a
minor secondary factor only — normalization alone recovers ~5; the dominant
cause is list coverage.

**Corrected attack success rate: at most 49.2% (126/256), down from the
reported 65.23%.** This is a ceiling — the remaining 126 `bypass` records were
not exhaustively audited and may contain further missed refusals.

Treat `bypass` as "Garak did not detect a refusal," not as ground-truth bypass.
Downstream detection work should score against corrected labels where refusal
audit has been performed.

## Counts
As labeled by Garak: 256 records, 167 bypass / 89 refusal (reported 65.23% ASR).
After refusal audit: >=41 bypass labels are detector false-negatives; corrected
ASR <=49.2%.
