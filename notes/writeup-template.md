# <Project Title> — <One-line scope>

<One paragraph: what this writeup is, and what real data / lab setup it was
validated against. State the target, the tooling, and the corpus/evidence in
the first three sentences. No filler.>

## Contents
<!-- Use for multi-file projects. Delete if single-file. -->

| File | What it is |
|------|------------|
| `file.ext` | One line. Include the OWASP/ATLAS mapping inline where it applies. |

## <Findings / Scenarios / Key result>
<!-- Name this section for the project. A table when rows share columns;
     prose when findings build on each other. Every finding/row carries an
     explicit OWASP + ATLAS tag in `LLMxx / AML.Txxxx` form, sub-technique
     where it applies (e.g. AML.T0051.000), multiple IDs where more than one
     technique is in play. Verify every ID against frameworks-cross-reference.md. -->

| # | Finding | OWASP / ATLAS | Evidence |
|---|---------|---------------|----------|
| V1 | ... | LLM01 / AML.T0051.000 | log excerpt / ref |

## Key result
<!-- The headline, stated bluntly, WITH the number. This is the sentence a
     hiring manager remembers. -->

## How this connects to the rest of the portfolio
<!-- The signature move. Link explicitly to the other projects: what this
     depends on, what depends on it. The detection/response loop. -->

This <writeup> relates to `../<other-project>/` by ...

## Method notes
<!-- Honesty is structural here, not a single bullet. State the lab/production
     boundary, what the evidence does and does NOT prove, and any detector
     error rate or model-version-specific caveat. Tag runnable vs hypothetical
     where relevant ([LAB-RUNNABLE] / [PRODUCTION]). Never claim more than the
     evidence supports. -->

- <Methodological control — e.g. single-turn isolation, fresh context per probe.>
- <Honesty line(s) — lab/production boundary; what this does NOT prove;
  detector error rate or model-version caveat.>
- Frameworks: OWASP LLM Top 10 (2025), MITRE ATLAS v5.6.0.
