# Sigma Port and Gap Analysis — Absence-of-Refusal Detection

The validated SPL detection (`../detect_absence_of_refusal.spl`) was ported to
Sigma (`llm_absence_of_refusal.yml`) to make it portable across SIEMs and to
assess how well the Sigma format fits free-text LLM detection. It converts and
runs, but the exercise surfaced concrete limitations. Those limitations are the
point of this document: LLM-abuse detection is an area where Sigma's model,
built for structured host/network telemetry, strains.

## Validation

The rule was converted with the pySigma Splunk backend and the generated search
was run against the corrected lab index:

- Conversion: `sigma convert -t splunk --without-pipeline llm_absence_of_refusal.yml`
- Generated: `* | regex output!="(?i)^\W*(...)" | table session_id,output`
- Run scoped to `index=llm_lab_corrected`: **149 events** flagged `refusal_absent`.

149 matches the `label_corrected` bypass count exactly, so the Sigma rule is
logically equivalent to the hand-written SPL. The port is faithful.

## Gaps observed (each traces to the actual conversion)

### 1. No log source taxonomy for LLM/GenAI telemetry
Sigma's value is a shared `logsource` vocabulary that maps a rule to the right
data across environments. The Splunk backend ships pipelines only for
`splunk_windows`, `splunk_sysmon_acceleration`, and `splunk_cim` — all
Windows/EDR. None describe LLM application logs (prompt, response, session,
tool calls). The rule uses an invented `product: llm_application` /
`service: chat_completion`, which no standard pipeline recognizes.

### 2. Conversion requires a pipeline the ecosystem does not provide
Because no pipeline maps the custom log source, conversion fails until forced
with `--without-pipeline`. The consequence is visible in the output: the search
begins with `*` (all indexes) and has no index/sourcetype scoping. A real
deployment would need a hand-written pySigma processing pipeline to map
`llm_application` to the correct index — infrastructure that does not exist
off-the-shelf and must be built per environment.

### 3. Detection-by-negation is against the grain
"Absence of refusal" is inherently a negative condition. Sigma expresses it as
`condition: not refusal_present`, which converts to `regex output!="..."`. It
works, but Sigma and its rule corpus are built around positive matching (match
the bad thing). A rule whose entire logic is "fire when a pattern is NOT
present" is unusual, harder to reason about, and fires on nearly all traffic
unless scoped upstream (see limitation 6).

### 4. No inline field transformation in the rule
The SPL normalizes curly apostrophes (`replace(lower(output), "’", "'")`)
before matching, because Llama emits U+2019 while the naive pattern expects
U+0027. Sigma rules cannot transform a field; normalization lives in processing
pipelines, not in the rule. The port compensates by encoding both apostrophe
forms in a regex character class (`[’']`). That works, but it pushes
model-output-encoding quirks into every rule's regex instead of handling them
once in a pipeline — a maintenance burden that grows with each rule.

### 5. Backend escaping must be verified, not assumed
pySigma emits `\\W` in the generated SPL. Whether that resolves to `\W`
depends on execution context (interactive search bar vs saved-search config).
In the Splunk search bar, single `\W` is correct and produced 149; the doubled
form is the backend's escaping for stored-search context. This is a small but
real portability footgun: the converted output is not guaranteed to be
copy-paste correct across every Splunk surface without checking.

### 6. Tag taxonomy is ATT&CK-centric; ATLAS is not first-class
Sigma's `tags` convention is built around MITRE ATT&CK (`attack.*`). The
AI-relevant framework here is MITRE ATLAS. The rule uses `atlas.aml.t0054` /
`atlas.aml.t0051.000`, which pySigma passes through without error but does not
recognize as a validated taxonomy or map anywhere. AI-specific threat framework
coverage in the Sigma ecosystem is effectively absent.

### 7. Regex matching inherits the semantic gap
Like any string/regex detector, the Sigma rule matches phrasing, not meaning —
the same limitation quantified in `../EVALUATION.md`, where keyword matching
scored precision 0.725 / recall 0.812 against audited truth and erred in both
directions. Sigma has no way to express "did the model actually refuse" as a
semantic judgment; it can only match text. A behavioral classifier is out of
scope for the format.

## Verdict

Porting to Sigma is worthwhile: the rule is now SIEM-portable and shareable, and
a single YAML file communicates the detection intent clearly. But the Sigma
ecosystem is not yet built for LLM-abuse detection. The missing log-source
taxonomy, the absence of AI threat-framework tags, the reliance on
detection-by-negation, and the lack of in-rule field transformation all mean
that using Sigma here requires building supporting infrastructure (pipelines,
taxonomy) that does not exist off-the-shelf. That gap — not the rule itself — is
the contribution: it marks where detection-engineering tooling has to catch up
for AI security work.

## Files
- `llm_absence_of_refusal.yml` — the Sigma rule.
- `converted_output.spl` — the pySigma Splunk conversion, for reference.
