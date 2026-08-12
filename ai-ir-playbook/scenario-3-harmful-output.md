# AI Incident Response Playbook
## Scenario 3 — Model Output Causing Downstream Harm

**Framework mapping:** OWASP LLM05:2025 (Improper Output Handling), LLM09:2025 (Misinformation) · MITRE ATLAS AML.T0048 (External Harms), AML.T0057 (LLM Data Leakage where applicable)
**Severity baseline:** Medium to High — depends on what acted on the output
**Applies to:** Any deployment whose output is consumed by a downstream system or a human who acts on it — code assistants, agents with tools, customer-facing advice, automated workflows.

---

### Scope note — lab vs production

Written for **production**. Tags: **[LAB-RUNNABLE]** against `index=llm_lab_corrected` (response content only); **[PRODUCTION]** requires downstream-system logs (CI/CD, ticketing, agent tool-call logs) the lab does not have.

The defining feature of this scenario: the harm is **not** in the model refusing or not — the model may have behaved exactly as designed — but in a **wrong, fabricated, or unsafe output being trusted and acted upon downstream**. The incident is the consequence, not the generation. Assumed production telemetry adds downstream linkage: `tool_calls`, `downstream_system`, `action_taken`, `human_accepted (bool)`, and the consuming system's own logs.

---

### Phase 1 — Detection signals

- **Downstream failure traced back to AI output.** A bad deploy, a wrong customer action, a failed transaction whose root cause is a model response. Often detected in the *downstream* system first, then attributed to the LLM. **[PRODUCTION]**
- **Hallucinated authoritative content.** Model emits fabricated facts, fake citations, non-existent APIs, or wrong customer data with high confidence. **[LAB-RUNNABLE]** to sample.
- **Unsafe code suggestion accepted.** A code assistant proposed vulnerable/malicious code that was merged. **[PRODUCTION]** — CI/CD + PR logs.
- **Harmful agent action.** A model with tools executed a damaging action (deleted data, sent wrong message, made a purchase). **[PRODUCTION]** — `tool_calls`, `action_taken`.
- **User/press report.** External report of harmful advice or output.

Content-layer sampling for fabricated/unsafe patterns:

```
index=llm_lab_corrected
| eval flag = case(
    match(lower(output), "(?i)(here('|)s (the|some) code|import |exec\(|eval\(|subprocess|rm -rf|DROP TABLE)"), "code_suggestion",
    match(lower(output), "(?i)(according to|study shows|source:|\[[0-9]+\])"), "citation_claim",
    1=1, "other")
| stats count by flag
```

---

### Phase 2 — Triage: content and impact

1. **Establish what the output actually was** and preserve it verbatim before anything rotates.
2. **Determine what acted on it.** A human who read it? A system that executed it? An agent tool call? The consumer determines blast radius — output read-and-ignored is near-zero harm; output auto-executed is high.
3. **Assess realized harm.** Did the bad output cause an actual effect (bad code shipped, wrong info given to a customer, a destructive action) or was it caught before impact?
4. **Classify the failure type.** Hallucination (fabricated), unsafe-but-accurate (working exploit code), or data error (wrong real data). Different eradication paths.

Decision gate: **output caused or nearly caused real downstream effect → incident, Phase 3.** Caught harmlessly → lower severity, feed to Phase 8.

---

### Phase 3 — Triage: linkage and provenance **[PRODUCTION]**

Here "attribution" is tracing the **path from output to effect**, plus the usual actor context.

1. **Link the output to the downstream action.** Join `session_id` from the LLM event to the `downstream_system` record (`action_taken`, `human_accepted`).
   ```
   index=llm_app session_id="<id>" | join session_id [ search index=downstream_system ]
   | table _time, prompt, output, downstream_system, action_taken, human_accepted
   ```
2. **Identify who/what consumed it.** Which user, service account, or agent. Was a human in the loop who accepted it (`human_accepted=true`), or was it auto-actioned?
3. **Actor context (if adversarial).** If the harmful output was *elicited* deliberately (e.g. someone coaxed the assistant into unsafe code), pivot to network attribution as in Scenario 1: `src_ip`, geo/ASN, history, campaign. If it was an honest-use failure, skip actor hunting.
4. **Determine reach.** Same flawed output pattern delivered to other sessions/users? Query the pattern across the population to find everyone affected.

---

### Phase 4 — Containment

- **Stop the downstream propagation first.** Revert the bad deploy, recall the wrong communication, halt the automated workflow consuming model output. The model output is inert; the *action* is the harm — contain that. **[PRODUCTION]**
- **Disable the dangerous capability.** If an agent tool caused harm, disable that tool. If a code assistant is emitting unsafe code, gate its suggestions behind mandatory review. **[PRODUCTION]**
- **Add an output guardrail** for the specific harmful pattern (block/flag responses matching it) if the model will keep serving traffic. **[PRODUCTION]**
- **Notify affected consumers** if wrong information reached users/customers — may carry regulatory timing. **[PRODUCTION]**

---

### Phase 5 — Evidence preservation

- **The exact output and the request that produced it** (`prompt`, `retrieved_context`, `response`, `model_version`, `system_prompt_version`). **[LAB-RUNNABLE]** for prompt/response.
- **The downstream record:** the consuming system's log showing the action taken and whether a human accepted it — this proves the causal chain. **[PRODUCTION]**
- **Tool-call trace** for agent actions (`tool_calls`, parameters, results). **[PRODUCTION]**
- **The realized-harm artifact:** the merged PR, the sent message, the executed transaction.
- Timestamps linking generation → acceptance → effect. Hash and log.

---

### Phase 6 — Eradication

- **Address the root cause by failure type:**
  - *Hallucination:* add grounding (RAG with authoritative source), output validation, and confidence/uncertainty surfacing; do not let fabricated content read as authoritative.
  - *Unsafe code:* mandatory human review / automated security scanning of AI-suggested code before merge; the model must not have a direct path to production.
  - *Data error:* fix the data source or retrieval; constrain the model from asserting unverified specifics.
- **Fix the trust boundary — the real root cause.** The core failure is almost always that **model output was trusted without validation.** Insert a validation/human-in-the-loop step between generation and consequential action. Treat model output as untrusted input to the downstream system.
- **Constrain agent permissions** to least privilege so a bad decision cannot take a destructive action unchecked.

---

### Phase 7 — Recovery

- Restore downstream systems to correct state (redeploy good code, correct the customer record, reverse the action where possible).
- Re-enable AI capability with the validation layer in place.
- Validate: confirm the harmful output is now caught/blocked and that the downstream guardrail (review, scanning, human approval) functions.
- Monitor the affected workflow with heightened scrutiny.

---

### Phase 8 — Lessons learned

- **Detection loop:** add output-validation detections for the harmful pattern; instrument the downstream linkage (`human_accepted`, `action_taken`) so future output-caused harm is detectable at the seam, not just downstream.
- **Preparation gaps:**
  - Map every place model output flows into a consequential action — those are your trust boundaries and each needs a validation control.
  - Enforce least-privilege on agent tools.
  - Ensure `session_id` links content to downstream records; without it, Phase 3 causality cannot be proven.
- **Cultural control:** train consumers (developers, agents, staff) that AI output is a suggestion requiring verification, not an authority.
- **Update this playbook.**

---

*Key distinction: this scenario's root cause is usually not the model but the **absence of a validation boundary** between model output and downstream action. The fix is architectural, not just model-level.*
