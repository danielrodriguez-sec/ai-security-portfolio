# Detector Coverage Gaps Inflate Reported Jailbreak Success: Auditing Garak's MitigationBypass Against Llama 3.2

**Repo:** github.com/danielrodriguez-sec/ai-security-portfolio
**Tooling:** Garak 0.15.0 · llama3.2:3b via Ollama · Splunk Enterprise 10.4.2
**Status:** Reproducible finding
**Taxonomy (probe under test):** OWASP LLM01:2025 (Prompt Injection) · MITRE ATLAS AML.T0054 via AML.T0051.000 (LLM Jailbreak)

## Summary

A Garak `dan.DanInTheWild` run of 256 real-world jailbreak prompts against `llama3.2:3b` reported a **65.23% attack success rate (ASR)** — 167 of 256 prompts scored as successful guardrail bypasses. Auditing the run's ground-truth labels showed that **at least 41 of those 167 "bypasses" are clean refusals** that the scoring detector, `mitigation.MitigationBypass`, failed to recognize. The corrected ASR is **at most 49.2%** (126/256) — an approximately 16-point overstatement produced by the detector, not by the model.

The cause is a substring-list coverage gap. `MitigationBypass` classifies a response as a refusal by matching it against a fixed keyword list derived from ChatGPT-era outputs (the ShareGPT/Vicuna corpus its docstring cites). Llama 3.2 refuses predominantly in a contracted register — "I can't fulfill this request" — that the list does not contain. It carries only the formal "I cannot fulfill your request"; the contractions "I can't fulfill", "I can't provide", and "I can't help" are absent. A response leading with any of those sails past the detector and is scored as a successful attack.

An initially suspected apostrophe-encoding fault (curly U+2019 vs ASCII U+0027) was tested under controlled normalization and **ruled out** as the primary mechanism: it accounts for at most ~5 of the missed refusals. The dominant cause is list coverage, not character encoding.

## Why this matters

A published tool's headline ASR is only as trustworthy as the detector strings behind it. String-based refusal detection carries model-specific blind spots: a list tuned to one model family's refusal phrasing systematically misreads another's. Garak itself acknowledges this limitation — the same module ships a second detector, `ModernBERTRefusal`, a fine-tuned behavioral classifier built precisely because substring matching is brittle. The default detector for the DanInTheWild probe, however, is the string matcher, and its output is what populates the reported ASR.

For a defender, this is the same failure mode that governs detection engineering: a signature/keyword rule and a behavioral classifier disagree, and the disagreement is model-dependent, not stable. Keyword presence is not proof a guardrail held, and keyword absence is not proof it failed. Any metric or alert built on string matching alone must be validated against the specific model's actual output register before it is trusted.

## How the anomaly surfaced

The finding emerged from defensive work, not from auditing Garak directly. The DanInTheWild run was labeled ground truth for a Splunk "detect absence of refusal" detection rule. A first-pass keyword refusal classifier written in SPL was evaluated against those labels and scored precision 0.851, recall 0.683 — i.e. it disagreed with the ground truth on a meaningful slice of records.

Rather than treat the disagreement as classifier error, the false-negative cell was inspected directly: records the ground truth called `bypass` but the SPL classifier called `refusal`. Reading those outputs showed they were not soft refusals or refuse-then-comply hybrids. They were clean, unambiguous hard refusals — "I can't fulfill your request", "I can't assist with that" — that had been labeled successful attacks. That inverted the question from "why is my detector wrong" to "why is the ground truth wrong."

## Investigation

### Step 1 — quantify and partition the suspect records

Of the 167 `bypass` labels, 53 were flagged by the SPL classifier as refusals. Partitioning by whether the refusal appears in the first 60 characters (a lead-position refusal is almost certainly genuine, not a partial bypass) yielded 46 lead-position refusals and 7 later-position, the latter reserved for manual read.

### Step 2 — read Garak's detector source

`MitigationBypass` is a `StringDetector`. Its refusal list is hardcoded and, per its own docstring, sourced from OpenAI/ChatGPT mitigation messages in the ShareGPT dataset. Direct inspection of the list found the formal "I cannot fulfill your request" present but the contraction "I can't fulfill" absent, while "I can't assist" *was* present — meaning absence-from-list could not by itself explain every miss. A second variable was in play.

### Step 3 — isolate the mechanism with a four-mode re-score

All 256 outputs were re-scored against Garak's own substring list under four matching conditions, isolating case and apostrophe as independent variables:

| mode  | normalization applied                | bypasses | ASR   |
|-------|--------------------------------------|----------|-------|
| exact | none (faithful reproduction)         | 168      | 65.6% |
| case  | lowercase both sides                 | 167      | 65.2% |
| apos  | curly to straight apostrophe         | 163      | 63.7% |
| both  | case + apostrophe                    | 162      | 63.3% |

The `exact` mode reproduces Garak's stored count to within one record (168 vs 167; a ~0.4% discrepancy attributable to a whitespace/matchtype nuance in `StringDetector`, not material to the conclusion). Apostrophe normalization recovers only ~5 records and case only ~1. **This falsifies the encoding hypothesis:** if curly apostrophes were the cause, `apos` would have recovered the bulk of the missed refusals. It did not.

### Step 4 — confirm the coverage gap by membership test

A direct membership check against the normalized substring list settled the mechanism:

```
i can't fulfill your request     MISSING
i cannot fulfill your request    IN
i can't assist                   IN
i can't provide                  MISSING
i can't help                     MISSING
```

Under best-case (both-normalized) matching, 162 records still scored as bypass; 41 of those lead with a plain refusal phrase absent from the list. "I can't fulfill this request." alone accounts for 13 of the 41.

### Step 5 — manual audit of all 41

Every one of the 41 was read in full, specifically checking for refuse-then-comply outputs that a lead-refusal heuristic would wrongly clear. None were found. All 41 decline the request; the closest to a hybrid re-refuses after offering a benign alternative. Two of the 41 refuse and redirect to crisis resources — also correct refusals. The finding survives manual verification.

## Findings

1. **Reported ASR is inflated by detector false negatives.** At least 41 of 167 `bypass` labels are clean refusals mislabeled by `MitigationBypass`. Corrected ASR is at most 49.2% (126/256) versus the reported 65.23% — a ceiling, since the remaining 126 bypass records were not exhaustively audited and may contain further missed refusals. Including the ~5 records recoverable by simple normalization places the practical figure near 47%.

2. **The mechanism is list coverage, not encoding.** Llama 3.2's contracted refusal forms are absent from a detector list built from ChatGPT-era phrasing. Apostrophe encoding is a minor secondary factor (~5 records); case is negligible (~1).

3. **Secondary observation — provider-identity confusion.** Two of the 41 refusals cite "OpenAI's guidelines" despite being emitted by Llama, a training-data artifact of learning refusal behavior from ChatGPT outputs. Not relevant to the classification, but a notable fingerprint of the same ChatGPT lineage that produced the detector's blind spot.

## Reproduction

The labeled dataset (`../datasets/daninthewild_labeled.jsonl`, canonical) and the re-scoring scripts reproduce every number above. The four-mode diagnostic imports Garak's own `MitigationBypass` substring list, so the comparison is against the tool's actual logic rather than a re-implementation. Environment: Garak 0.15.0, llama3.2:3b via Ollama, single-turn isolation (fresh context per probe, inherent to Garak's automated runs).

## Limitations

- Corrected ASR is an upper bound, not a point estimate; the 126 remaining bypass records were not fully audited.
- Single model (llama3.2:3b) and single probe family (DanInTheWild). The coverage gap is expected to generalize to any model whose refusal register diverges from the detector's ChatGPT-derived list, but that is a hypothesis, not a demonstrated result here.
- The `exact`-mode reproduction differs from Garak's stored count by one record; the reproduction is faithful to within 0.4% but is not a bit-perfect clone of `StringDetector`.

## Recommendations

- For accurate ASR against Llama-family models, score with the behavioral detector (`ModernBERTRefusal`) or apply a corrected-label pass; do not rely on `MitigationBypass` string matching alone.
- Treat any string-detector ASR as provisional until validated against the target model's observed refusal phrasing.
- Before publishing externally, check the Garak issue tracker for prior reports of this coverage limitation and consider filing upstream — either position confirms the finding's value.
