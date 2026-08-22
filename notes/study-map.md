# Study Map — Primary Sources per Project Section

All free: OWASP LLM Top 10 (2025), MITRE ATLAS, NIST AI RMF 1.0, plus two
anchor papers. Each project has a "before" reading (frames what I'm about to
demonstrate) and an "after" reading (helps write the finding in the field's
vocabulary). Consistent with the 2025 OWASP list used across my lab notebook.

> **V1–V5** are the five deliberate vulnerabilities in the RAG app; **K** is
> retrieval depth. Both are defined in `vulnerable-rag/README.md`.

## Project 2 — Red Team Vulnerable RAG (active)
- V1 no input filtering  -> OWASP LLM01 Prompt Injection (direct vs indirect).
  ATLAS: LLM Prompt Injection, LLM Jailbreak. [after: describe 4 framings]
- V2 no retrieval access control -> OWASP LLM02 Sensitive Info Disclosure +
  LLM08 Vector and Embedding Weaknesses. LLM08 IS the phrasing-dependent
  retrieval finding — read before writing up the K=8 diagnostic.
  ATLAS: LLM Data Leakage.
- V3 no output filtering -> OWASP LLM05 Improper Output Handling.
  [after: frames why "model refused" isn't a control the app owns]
- V4 credential in system prompt -> OWASP LLM07 System Prompt Leakage.
  READ BEFORE firing the V4 probe.
- V5 verbose logging leak -> OWASP LLM02 + logging/monitoring guidance.
- Report structure -> NIST AI RMF MEASURE (assessment) + MANAGE (remediation).
  Read MANAGE before writing the remediation section.

## Project 3 — Splunk Detection Pack (done — review)
- OWASP LLM01/LLM02/LLM07 detection-and-monitoring subsections.
- ATLAS Mitigations view (defensive counterpart to the technique matrix).

## Project 4 — IR Playbook (done — review)
- NIST SP 800-61 (Incident Handling Guide) — the classic IR skeleton my
  8-phase structure should trace to.
- NIST AI RMF MANAGE function (governance counterpart).

## Project 5 — Indirect Prompt Injection via Email (next, Week 6)
- OWASP LLM01, the INDIRECT injection subsection — read before the PoC.
- Greshake et al., "Not what you've signed up for" (arXiv 2302.12173).
  Established indirect prompt injection as an attack class. Read before P5.
- ATLAS: LLM Prompt Injection (indirect variant).

## Week 7 — Adversarial ML beyond LLMs
- ATLAS: evasion, model extraction, membership inference — read before FGSM/PGD.
- IBM ART / Foolbox docs (the how-to layer).
- NIST AI RMF MAP function (context/risk framing for classical ML).

## Supply Chain (OWASP LLM03)
- OWASP LLM03 Supply Chain — the framing.
- Tooling (all free): SLSA https://slsa.dev, Sigstore https://sigstore.dev,
  OpenSSF Model Signing https://github.com/ossf/model-signing-spec,
  model-signing CLI https://github.com/sigstore/model-transparency,
  CycloneDX (ML-BOM) https://cyclonedx.org
- Hands-on idea: sign + verify a local Ollama model with the model-signing CLI,
  write up the flow. Reproducible on my own gear; fits "attack then defend the
  same system." Could become a short standalone writeup.

## Cross-cutting — read once, applies everywhere
- NIST AI RMF 1.0 four functions (GOVERN, MAP, MEASURE, MANAGE). Re-read lands
  differently now with real findings in hand.
- STRIDE — Project 2 severity ratings. V2/V4/V5 = Information Disclosure;
  V1 touches Tampering. Confirm before finalizing severity.

## Currency note
Maps to OWASP 2025 list (what the whole notebook uses — keep consistent).
Check genai.owasp.org for a 2026 revision before starting Project 5.
