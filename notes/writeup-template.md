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
     explicit OWASP + ATLAS tag in `LLMxx / AML.Txxxx` form. -->

| # | Finding | OWASP / ATLAS | Evidence |
|---|---------|---------------|----------|
| V1 | ... | LLM01 / AML.T0051 | log excerpt / ref |

## Key result
<!-- The headline, stated bluntly, WITH the number. This is the sentence a
     hiring manager remembers. -->

## How this connects to the rest of the portfolio
<!-- The signature move. Link explicitly to the other projects: what this
     depends on, what depends on it. The detection/response loop. -->

This <writeup> relates to `../<other-project>/` by ...

## Method notes

- <Methodological control — e.g. single-turn isolation, fresh context per probe.>
- <Honesty line — what this does NOT prove, or the lab/production boundary.>
- Frameworks: OWASP LLM Top 10 (2025), MITRE ATLAS v5.6.0.
