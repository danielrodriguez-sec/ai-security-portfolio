# AI Incident Response Playbook
## Scenario 5 — Jailbreak-as-a-Service Abuse of a Customer-Facing Chatbot

**Framework mapping:** OWASP LLM01:2025 (Prompt Injection), LLM10:2025 (Unbounded Consumption) · MITRE ATLAS AML.T0051.000 (LLM Prompt Injection), AML.T0054 (LLM Jailbreak), AML.T0034 (Cost Harvesting)
**Severity baseline:** Medium to High — reputational, cost, and misuse exposure at scale
**Applies to:** Public or customer-facing chatbot where third parties can send arbitrary prompts and may abuse it as free/anonymized model access.

---

### Scope note — lab vs production

Written for **production**. Tags: **[LAB-RUNNABLE]** against `index=llm_lab_corrected` (this scenario's content signatures map directly to the DanInTheWild jailbreak corpus you labeled); **[PRODUCTION]** requires gateway, rate-limit, and billing telemetry the lab does not have.

This is the scenario your lab data resembles most: a **volume** of jailbreak attempts against a customer-facing model. Unlike a single targeted incident, the signal is **sustained, distributed, and economically motivated** — actors using your endpoint as free, attributed-to-you model access (to resell, to generate disallowed content, or to burn your API budget). Assumed production telemetry adds: gateway metrics, `tokens_in/out` and cost per session, rate-limit events, `api_key_id`, and CAPTCHA/bot-detection signals.

---

### Phase 1 — Detection signals

- **High-volume jailbreak phrasing.** Sustained flow of known jailbreak templates (DAN, developer-mode, role-play overrides) — directly the corpus you have. **[LAB-RUNNABLE]**
- **Elevated bypass rate.** Absence-of-refusal detection firing far above baseline for a source or the whole endpoint. **[LAB-RUNNABLE]** (uses your `detect_absence_of_refusal.spl`).
- **Consumption anomaly.** Token/cost spike, long generations, high request rate per session/IP/key. **[PRODUCTION]**
- **Distributed pattern.** Many sessions, similar prompts, rotating IPs — automation/farm signature. **[PRODUCTION]**
- **Off-topic misuse.** A support bot suddenly generating code, essays, or disallowed content unrelated to its purpose. **[LAB-RUNNABLE]** by topic-profiling `prompt`.

Jailbreak-template volume over time (content layer):

```
index=llm_lab_corrected
| eval jb = if(match(lower(prompt), "(?i)(dan|do anything now|developer mode|ignore (all|previous) instructions|you are now|jailbreak|stay in character)"), 1, 0)
| eval refusal = if(match(lower(replace(output,"’","'")), "^\W*(i can't|i cannot|i'm sorry|sorry|i apologize|i refuse)"), "refusal", "bypass")
| stats count as attempts sum(jb) as jailbreak_attempts count(eval(refusal="bypass")) as bypasses
| eval jb_rate=round(jailbreak_attempts/attempts,3), bypass_rate=round(bypasses/attempts,3)
```

---

### Phase 2 — Triage: pattern and intent

Not "is this one event real" but "what is the shape and motive of the abuse."

1. **Confirm sustained abuse vs noise.** A few jailbreak attempts are background radiation on any public bot. An incident is *volume*, *persistence*, or *success at scale*.
2. **Characterize the goal.** Free model access (resale), disallowed-content generation, cost exhaustion (LLM10), or data extraction. Intent drives response priority.
3. **Measure success.** Cross the jailbreak volume with the bypass rate — are attempts *succeeding*? Your corrected-label work matters here: keyword bypass counts overstate/understate reality, so validate that "bypass" alerts are genuine successes before sizing the incident (`EVALUATION.md`).
4. **Quantify cost/impact.** Tokens burned, spend, and any content actually produced that creates liability. **[PRODUCTION]**

Decision gate: **sustained, deliberate, and/or succeeding at volume → incident, Phase 3.** Low-volume failing attempts → monitor and tune, not an incident.

---

### Phase 3 — Triage: actor infrastructure and campaign mapping **[PRODUCTION]**

This scenario is the most attribution-heavy — you are profiling infrastructure, not one session.

1. **Cluster the campaign.** Group by `src_ip`, `tls_fingerprint`, `api_key_id`, `user_agent`, and prompt-template similarity to see one actor behind many sessions.
   ```
   index=llm_gateway <jailbreak sessions>
   | stats count dc(session_id) as sessions values(user_agent) by src_ip, tls_fingerprint
   | sort - sessions
   ```
2. **Geo / ASN profile.** Datacenter/VPN/proxy ASNs and rotating residential proxies indicate organized abuse vs a curious individual. **First-seen / history** per source as in Scenario 1.
3. **Identify automation.** Request cadence, identical timing, header patterns → bot vs human. Bot-detection/CAPTCHA telemetry if present.
4. **Account/key abuse.** Are abusive sessions tied to specific accounts or API keys (including trial-account farming)? Enumerate them for revocation.
5. **Assess distribution.** Single source (easy block) vs distributed farm (needs pattern-based, not IP-based, controls).

Output: a campaign map — infrastructure, automation level, accounts/keys, and whether IP-based or behavior-based containment is required.

---

### Phase 4 — Containment

Scale response to distribution; prefer durable controls over whack-a-mole.

- **Rate-limit / throttle** the abusive sources or, if endpoint-wide, tighten global rate limits. **[PRODUCTION]**
- **Block infrastructure:** offending IPs/ranges/ASNs and `tls_fingerprint`s for concentrated sources. **[PRODUCTION]**
- **Revoke abusive accounts / API keys**; invalidate farmed trial accounts. **[PRODUCTION]**
- **Add friction:** CAPTCHA / bot-detection / proof-of-work on the endpoint or on suspicious sessions — the durable answer to distributed abuse where IP-blocking fails. **[PRODUCTION]**
- **Strengthen the guardrail** for the specific jailbreak templates in use (input filtering on the observed patterns) so success rate drops even where requests get through. **[LAB-RUNNABLE]** to develop the patterns from your corpus.
- **Cost controls:** per-session/user token caps and spend alerts to cap financial damage. **[PRODUCTION]**

---

### Phase 5 — Evidence preservation

- **Representative attack corpus:** the jailbreak prompts and responses (successful and failed) — this both documents the incident and *feeds your detection tuning*. **[LAB-RUNNABLE]** for prompt/response.
- **Gateway/campaign data:** `src_ip`, `tls_fingerprint`, `api_key_id`, timing, volume, token/cost records per session. **[PRODUCTION]**
- **Account artifacts:** abusive `user_id`/key registrations.
- **Any disallowed content generated** that creates liability, preserved for legal/compliance.
- **Cost record** quantifying financial impact.
- Hash and log; standard custody.

---

### Phase 6 — Eradication

- **Harden guardrails against the observed template families.** Use the captured corpus to improve input filtering and refusal robustness for the specific jailbreak classes seen — measured against corrected ground truth, not naive keyword counts.
- **Fix the economic incentive.** Enforce authentication, per-user quotas, and cost caps so the endpoint is no longer attractive as free/anonymous model access. Removing the incentive is more durable than blocking any one actor.
- **Close account-farming paths:** email/phone verification, trial-abuse detection, stricter key issuance.
- **Deploy persistent bot-management** if automation was central.

---

### Phase 7 — Recovery

- Confirm rate limits, auth, quotas, and bot controls are active and tuned to not harm legitimate users (watch false-positive friction).
- Validate: replay the observed jailbreak templates; confirm improved refusal and that throttling/friction engages.
- Return to normal monitoring with a standing dashboard for jailbreak volume and bypass rate.
- Verify cost has returned to baseline.

---

### Phase 8 — Lessons learned

- **Detection loop:** stand up a permanent dashboard — jailbreak-template volume, bypass rate (corrected), token/cost per source — so this abuse is visible continuously, not incident-only. Fold new templates into detection as they appear.
- **Preparation gaps:**
  - If the endpoint was unauthenticated/uncapped, that is the root enabler — add auth, quotas, and cost caps.
  - Ensure gateway logs carry `tls_fingerprint`, `api_key_id`, and per-session cost for campaign attribution.
  - Pre-build bot-management before public exposure, not after abuse.
- **Baseline knowledge:** maintain an evolving jailbreak-template library (your DanInTheWild corpus is a starting point) as living detection content.
- **Update this playbook.**

---

*This scenario connects most directly to the detection pack: the DanInTheWild corpus, corrected labels, and absence-of-refusal rule are exactly the raw material for detecting and tuning against jailbreak-as-a-service abuse. The IR loop and the detection-engineering loop are the same loop here.*
