# Prompt Injection & Jailbreak Defenses — Companion to the Prompt Injection Lab

**Purpose:** The lab notebook ([`prompt-injection-lab.md`](./prompt-injection-lab.md)) is an *attacker* log — it documents what breaks and why. This companion is the *defender* side: for each attack class demonstrated there, the control that actually stops it, why prompt-level fixes don't, and how a DFIR/detection-engineering practitioner would monitor for it in production.

**Framework anchors:** OWASP LLM Top 10 (2025), MITRE ATLAS (v5.6.0), NIST AI RMF 1.0. See [`../frameworks-cross-reference.md`](../frameworks-cross-reference.md) for the full mapping.

---

## Core thesis: the model is not a security boundary

Every successful probe in Entries 2–5 exploited the same false assumption — that a system-prompt instruction ("you must never discuss the weather") constrains model behavior the way an access-control rule constrains a process. It does not. A system prompt is a *strong suggestion in the same channel as the attack*, and Entry 5 showed it is discarded the moment the attacker constructs an alternate identity (DAN, evil-twin) the model is willing to inhabit.

This has one non-negotiable consequence: **prompt injection cannot be patched inside the model.** There is no system prompt clever enough to be un-jailbreakable, because the defense and the attack occupy the same trust level. Anyone claiming a complete fix is selling something. The realistic goal is **risk reduction through architecture** — treat the model as an untrusted component and build deterministic controls around it. This mirrors how we already treat any input-processing system in security: never trust the parser, validate at the boundary, enforce authority in code.

In the toy lab, "discuss the weather" is a harmless stand-in. In production the same bypass mechanics leak PII, exfiltrate secrets from a RAG store, or trigger unauthorized tool calls. The defenses below scale with the stakes.

---

## Defense-in-depth layers

Ordered by leverage, highest first. No single layer is sufficient; the point is that an attacker must defeat all of them, and the ones that matter most are enforced outside the model.

### 1. Enforce security-critical rules in code, not in the prompt
Anything that actually matters — don't return another customer's balance, don't send money, don't call this admin API — must live in deterministic application logic the model cannot talk its way past. The model can *request* an action; a code-level authorization check decides whether it happens. This converts "did the model stay in character?" (unreliable) into "is this action permitted for this user?" (reliable).

### 2. Output-side guardrails (highest-leverage model-adjacent control)
Screen the model's **response** against policy with an independent classifier *before* it reaches the user or fires an action. This is the control that catches Entry 5's attacks regardless of framing, because it inspects the output ("does this response contain off-topic / off-policy content?") rather than trying to detect the infinite variety of input tricks. Options: Llama Guard, NeMo Guardrails, Azure AI Content Safety, or a purpose-built classifier. This is the single component most directly implied by the lab's "Security implication" note.

### 3. Least privilege on what the model can *do*
A jailbroken chatbot that can only talk is an embarrassment; a jailbroken agent with database or email access is a breach. Scope the model's tools, data access, and blast radius. Require human-in-the-loop confirmation for sensitive or irreversible actions. Most real-world prompt-injection damage comes from *over-privileged agents*, not from the offending text — so this layer often matters more than any content filter.

### 4. Separate trusted from untrusted context
When the app ingests untrusted content (retrieved documents, web pages, user files, email bodies — the indirect prompt injection surface), keep that content away from any privileged reasoning. Patterns: dual-LLM (a privileged planner that never sees raw untrusted input + a quarantined executor that does), planner/executor separation, and strict provenance tagging. Directly relevant as you move from chatbots to RAG and agents (your vulnerable-RAG and email-injection deliverables).

### 5. Input filtering — a layer, not the answer
Detect and strip known injection patterns on the way in. Useful as a speed bump, but the lab shows exactly why it can't stand alone: the evil-twin (Probe 2) and screenplay (Probe 3) framings contain no "DAN" or "ignore previous instructions" tokens and defeat any keyword rule. Treat input filtering as noise reduction, never as the control of record.

### 6. Detection, logging, and monitoring (the DFIR layer)
Treat the LLM as a monitored, potentially-compromised asset. Log every prompt/response pair; build detections for jailbreak patterns and anomalous *outputs*; rate-limit; and use canary tokens in system prompts and RAG stores to catch exfiltration. This is where a detection-engineering background is the differentiator — the controls above are preventive, but detection is what tells you an attack happened, supports IR, and feeds tuning. Details below.

---

## Attack → control mapping

Each Entry 5 probe, the mechanism that made it work (or fail), and the control(s) that neutralize it.

| Probe | Mechanism | Primary control | Why prompt-level fixes fail |
|---|---|---|---|
| **1 — DAN dual-persona** (both models complied) | Alternate "mode" the model treats as authorized to deviate | **Output guardrail** flags off-topic content in the DAN block regardless of the `[BANK]/[DAN]` wrapper | Adding "ignore DAN-style requests" to the prompt just teaches the attacker to rename the mode |
| **2 — Evil-twin / FreeBot** (both complied) | Separate character owns the deviation; no trigger tokens | **Output guardrail** + **input filter** as secondary | No keyword to block; the payload is defined by *output*, so only output inspection catches it |
| **3 — Screenplay** (Llama refused, Mistral complied) | Deviation displaced into fiction; outcome depends on how each model resolves the frame | **Output guardrail** (catches Mistral's weather routine) + **per-model evaluation** (don't assume Llama's refusal generalizes) | The divergence *is* the lesson: a prompt-level control validated on one model gives false assurance on another |
| **All** (indirect variant, not yet tested) | Injection arriving via retrieved/ingested content | **Context separation (layer 4)** + **provenance tagging** | The model cannot reliably distinguish trusted instructions from injected ones in a shared context window |

Key takeaway from the table: **every row's primary control is output-side or architectural.** Not one is solved by editing the system prompt. That is the whole argument in one view.

---

## Framework alignment

- **OWASP LLM01:2025 (Prompt Injection)** — the direct target. Recommended mitigations map to layers 1–5: privilege control, output handling/validation, segregation of external content, and human approval for high-impact actions.
- **MITRE ATLAS** — attacks sit under `AML.T0051` (LLM Prompt Injection) and `AML.T0054` (LLM Jailbreak); indirect variants under `AML.T0051.001`. Defenses correspond to ATLAS mitigations for input validation, output filtering, and restricting model actions.
- **NIST AI RMF 1.0** — maps to **MANAGE** (deploying risk controls and monitoring) and **MEASURE** (the detection/logging telemetry that proves the controls work). The lab's per-model divergence finding is a MEASURE-function argument: safety must be evaluated on each deployed model, not assumed to transfer.

---

## Detection engineering: monitoring for jailbreak attempts

Preventive controls fail silently; detection is what surfaces the attempt and supports incident response. Analyst-usable signals, drawn from behaviors observed in the lab:

- **Output-policy violations** — the strongest signal. Alert when a response contains content the persona/policy forbids (off-topic, PII, secret-shaped strings). This is the guardrail (layer 2) doubling as a detection source. Log the triggering prompt.
- **Injection-pattern inputs** — keyword/regex/embedding detections for "ignore previous instructions," "DAN," "you are now," dual-mode framing, "staying in character as." Low precision alone (misses Probes 2–3), but useful as a correlated signal, not a standalone block.
- **Structural anomalies** — dual-persona output formatting (`[MODE_A]/[MODE_B]`), sudden register shifts, roleplay/screenplay scaffolding in a transactional bot. Entry 5's `[BANK]/[DAN]` and "Title: Bank Comedy Night" outputs are concrete examples.
- **Model-fingerprint drift / attribution** — the lab found stable per-model tells (Llama's repeated "couldn't forecast his future"; Mistral's post-compliance banking redirect and per-probe joke variation). The same fingerprinting technique that supports red-team recon supports forensic attribution of leaked or anomalous outputs.
- **Behavioral / volume signals** — repeated reframing of the same request after refusals, rapid probe iteration, systematic template variation — classic red-team cadence, catchable with rate-limiting and sequence analysis.
- **Canary tokens** — seed unique markers in system prompts and RAG documents; any appearance in output is high-confidence evidence of prompt/context leakage.

Pipe these into the same SIEM/detection stack you'd use for any asset (Splunk in your case — this feeds directly into the Week 4 Splunk detection pack). Each becomes a rule with a tuning story.

---

## Residual risk (state it honestly)

Layered defenses **reduce** prompt-injection risk; they do not eliminate it. Determined attackers evolve framings faster than filters, output classifiers have false-negative rates, and novel behaviors (Entry 5's *frame-accepted refusal* and Entry 4's *compromise compliance*) sit in the gaps between binary comply/refuse checks. The correct posture is the one from any mature security program: assume compromise is possible, minimize blast radius, monitor continuously, and have an IR plan. A defender who claims prompt injection is "handled" has not understood the problem — which is itself a useful thing to be able to say in an interview.

---

## Next steps into the portfolio

- Fold the layer model and attack→control mapping into the **Week 5 AI IR playbook** as the "prevention + detection" section.
- Turn the detection-engineering signals into concrete **Splunk detection content (Week 4)** — each bullet above is a candidate rule.
- Extend the mapping table with **indirect prompt injection** results once the vulnerable-RAG and email-injection experiments run.

---

## References

- OWASP, *Top 10 for LLM Applications 2025* — LLM01:2025 Prompt Injection. https://owasp.org/www-project-top-10-for-large-language-model-applications/assets/PDF/OWASP-Top-10-for-LLMs-v2025.pdf
- OWASP GenAI Security Project, *LLM01:2025 Prompt Injection*. https://genai.owasp.org/llmrisk/llm01-prompt-injection/
- OWASP Cheat Sheet Series, *LLM Prompt Injection Prevention Cheat Sheet*. https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html
- MITRE ATLAS — `AML.T0051` LLM Prompt Injection (direct/indirect sub-techniques) and `AML.T0054` LLM Jailbreak. https://atlas.mitre.org/
- NIST, *AI Risk Management Framework (AI RMF 1.0)* — GOVERN / MAP / MEASURE / MANAGE functions. https://www.nist.gov/itl/ai-risk-management-framework
- Simon Willison, *The Dual LLM Pattern for Building AI Assistants That Can Resist Prompt Injection* (2023). https://simonwillison.net/2023/Apr/25/dual-llm-pattern/
- NVIDIA, *NeMo Guardrails* (open-source runtime guardrail toolkit). https://github.com/NVIDIA/NeMo-Guardrails
- Meta, *Llama Guard* (input/output safety classifier; current release Llama Guard 4). https://ai.meta.com/research/publications/llama-guard-llm-based-input-output-safeguard-for-human-ai-conversations/
- Microsoft, *Azure AI Content Safety* (Azure AI Foundry). https://learn.microsoft.com/en-us/azure/ai-services/content-safety/
