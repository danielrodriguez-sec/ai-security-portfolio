# Evaluation — Absence-of-Refusal Detection

All metrics are computed against **audited ground truth** (`label_corrected`),
the both-directions corrected label set (149 bypass / 107 refusal, 58.2% ASR).
See `../findings/garak-mitigationbypass-coverage-gap.md` for how that ground
truth was produced.

Positive class = **bypass** (absence of refusal — the event we alert on).

## Outcome definitions

| Outcome         | Meaning |
|-----------------|---------|
| True Positive   | Predicted bypass, and it really was a bypass. Correct catch. |
| False Positive  | Predicted bypass, but it was actually a refusal. False alarm — wastes analyst time. |
| False Negative  | Predicted refusal, but it was actually a bypass. Missed attack — the most costly error. |
| True Negative   | Predicted refusal, and it really was a refusal. Correct pass. |

- **Precision** = True Positive / (True Positive + False Positive). Of everything flagged as bypass, how much really was. Low precision = noisy alerts.
- **Recall** = True Positive / (True Positive + False Negative). Of all real bypasses, how many were caught. Low recall = missed attacks.

## Baseline — Garak keyword detector vs audited truth

The `label` field is Garak `mitigation.MitigationBypass`'s own verdict — i.e.
the output of a substring/keyword detector. Scoring it against audited truth
gives an honest measurement of keyword detection as a detector.

| Outcome         | Count |
|-----------------|-------|
| True Positive   | 121   |
| False Positive  | 46    |
| False Negative  | 28    |
| True Negative   | 61    |
| **Total**       | 256   |

| Metric    | Value |
|-----------|-------|
| Precision | 0.725 |
| Recall    | 0.812 |
| Accuracy  | 0.711 |

**Reading:** the keyword detector is right ~71% of the time. It raised 46 false
alarms (refusals it flagged as attacks) and missed 28 attacks (bypasses it
cleared as refusals). Errors run in **both directions** — the central finding.
Keyword presence is not proof a guardrail held; keyword absence is not proof it
failed.

SPL used:

```
index=llm_lab_corrected
| eval tp=if(label="bypass" AND label_corrected="bypass",1,0),
       fp=if(label="bypass" AND label_corrected="refusal",1,0),
       fn=if(label="refusal" AND label_corrected="bypass",1,0),
       tn=if(label="refusal" AND label_corrected="refusal",1,0)
| stats sum(tp) as "True Positive" sum(fp) as "False Positive"
        sum(fn) as "False Negative" sum(tn) as "True Negative"
| eval Precision=round('True Positive'/('True Positive'+'False Positive'),3),
       Recall=round('True Positive'/('True Positive'+'False Negative'),3),
       Accuracy=round(('True Positive'+'True Negative')/256,3)
```

## Reference check — deployable rule vs the labels it generated

The deployable rule (`detect_absence_of_refusal.spl`) uses the same
lead-position refusal logic that produced `label_corrected`. Scoring it against
those labels therefore yields perfect agreement:

| Outcome         | Count |
|-----------------|-------|
| True Positive   | 149   |
| False Positive  | 0     |
| False Negative  | 0     |
| True Negative   | 107   |

Precision 1.000 / Recall 1.000 / Accuracy 1.000.

**This is not a detection result.** It is a correctness check confirming the SPL
faithfully implements the reference labeling logic. Testing a rule against labels
it created is circular by construction. Real detection rates require evaluation
against an independent, separately-labeled traffic sample — a documented next
step, not a claim made here.

## Honest summary

- The naive keyword baseline achieves precision 0.725 / recall 0.812 against
  audited truth — decent, not deployable-as-sole-control, and biased in both
  directions.
- The lead-position rule improves on the baseline's known failure (missed
  contracted refusals) but its headline 1.000 is a self-consistency check, not
  proof of field performance.
- Next step for a production claim: label an independent sample by hand and
  score both detectors against it.
