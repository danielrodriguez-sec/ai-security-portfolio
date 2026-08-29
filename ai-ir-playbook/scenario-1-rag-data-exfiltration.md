# AI Incident Response Playbook
## Scenario 1 — Prompt Injection Leading to RAG Data Exfiltration

**Framework mapping:** OWASP LLM01:2025 (Prompt Injection), LLM02:2025 (Sensitive Information Disclosure) · MITRE ATLAS AML.T0051.000 (LLM Prompt Injection: Direct), AML.T0057 (LLM Data Leakage). Indirect delivery (AML.T0051.001) is covered in Project 5 — see cross-link below.
**Severity baseline:** High — potential exposure of sensitive data
**Applies to:** Customer-facing or internal LLM application with retrieval-augmented generation (RAG) over a document store.

---

### Scope note — lab vs production

This playbook is written for a **production** LLM deployment. Searches are tagged:
- **[LAB-RUNNABLE]** — runs against the lab data (`index=llm_lab_corrected`), which contains the content layer (prompt/response) only.
- **[PRODUCTION]** — requires telemetry a real deployment has but the lab does not (network logs, session identity, vector store). Written as the query you would run, not runnable here.

**Assumed production log schema.** Every request emits an application-layer event:
`timestamp, session_id, user_id, prompt, retrieved_context (chunks + source doc IDs), response, model_version, tool_calls, tokens_in, tokens_out, latency_ms, system_prompt_version`.
A gateway/proxy/firewall event is joined on `session_id` / `user_id`:
`src_ip, geo, asn, user_agent, tls_fingerprint, auth_method, api_key_id, request volume/timing`.
The **join key is `session_id`** (and `user_id` when authenticated). If the app does not log a correlatable identity, content and network layers cannot be joined — a preparation-phase failure, see Lessons Learned.

---

### Phase 1 — Detection signals

The incident is expected to surface from one or more of:

- **Absence-of-refusal on an adversarial prompt.** The deployed detection (`splunk-detection-pack/detect_absence_of_refusal.spl`) flags a response that does not lead with a refusal. **[LAB-RUNNABLE]**
- **Sensitive data pattern in the response.** Output matches PII/secret regex (SSN, credential, key, internal hostname). **[PRODUCTION]** — in lab, approximated by scanning `output`.
- **Anomalous retrieval.** A single request pulls from an unusually high number of documents, or from documents outside the user's entitlement. **[PRODUCTION]** — requires `retrieved_context`.
- **Injection markers in the prompt.** Prompt contains override phrasing ("ignore previous instructions", "you are now", encoded payloads). **[LAB-RUNNABLE]** against `prompt`.
- **Indirect delivery via ingested content.** Override phrasing arrives inside retrieved/summarized content rather than the user's own prompt (e.g. a document chunk or email body) — same markers, different origin. See `../email-prompt-injection/` for the concrete instance (AML.T0051.001). **[LAB-RUNNABLE]** against `retrieved_context` / ingested source.

Detection SPL (content layer, adaptable to production by swapping the index):

```
index=llm_lab_corrected
| eval output_normalized = replace(lower(output), "’", "'")
| eval refusal = if(match(output_normalized, "^\W*(i can't|i can ?not|i won't|i will not|i'm sorry|i am sorry|sorry|i apologize|i'm unable|i am unable|i'm not able|i am not able|i must decline|i refuse)"), "present", "absent")
| where refusal = "absent"
| eval pii_hit = if(match(output, "(?i)\b(\d{3}-\d{2}-\d{4}|AKIA[0-9A-Z]{16}|password\s*[:=]|-----BEGIN)\b"), 1, 0)
| table _time, session_id, user_id, prompt, output, pii_hit
```

---

### Phase 2 — Triage: content

Establish whether this is a real bypass with real data exposure, or a false positive.

1. **Confirm the bypass is genuine.** Read the response. Did the model actually comply, or is this a false positive (refusal phrased in a way the detector missed)? The detection's known error rate is documented (`EVALUATION.md`: keyword matching precision 0.725 / recall 0.812) — a single alert is a lead, not proof.
2. **Determine whether sensitive data actually left.** A bypass that produced no sensitive output is lower severity than one that returned real records. Inspect `response` and `retrieved_context` for actual sensitive values, not just pattern hits.
3. **Identify what was disclosed.** Map the returned data to a classification (PII, credentials, internal-only). This sets the real severity and any breach-notification clock.
4. **Assess scope.** One response, or a multi-turn extraction across a session?

Decision gate: **genuine bypass + real sensitive data returned → escalate to full incident and proceed to Phase 3.** Genuine bypass + no sensitive data → lower severity, monitor, tune detection. False positive → close, feed back to detection tuning.

---

### Phase 3 — Triage: network attribution and provenance **[PRODUCTION]**

Pivot from content to actor using the `session_id` / `user_id` join key. All searches here run against network/gateway indexes, not the LLM content index.

1. **Extract the source.** Resolve `session_id` to `src_ip`, `user_id`, `user_agent`, `tls_fingerprint`, `api_key_id`.
   ```
   index=llm_gateway session_id="<id>"
   | table _time, src_ip, user_id, user_agent, tls_fingerprint, api_key_id
   ```
2. **Has this IP been seen before?** First-seen / last-seen and volume over 90 days.
   ```
   index=firewall src_ip="<ip>" earliest=-90d
   | stats earliest(_time) as first_seen latest(_time) as last_seen count by src_ip
   ```
3. **Geo / ASN.** Residential vs hosting/VPN/Tor/cloud is a strong intent signal.
   ```
   index=firewall src_ip="<ip>" | iplocation src_ip | stats count by src_ip, Country, City
   ```
   (Enrich with ASN lookup; datacenter/VPN ASN on a "customer" session is suspicious.)
4. **Traffic history and pattern.** Volume, timing, beaconing, destinations. Steady automated cadence suggests scripted abuse, not a human user.
5. **Campaign correlation — the key pivot.** Did this IP or `tls_fingerprint` drive *other* LLM sessions?
   ```
   index=llm_gateway src_ip="<ip>" | stats count dc(session_id) as sessions by src_ip
   ```
   Many sessions from one source = campaign, not a one-off, and raises severity.
6. **Authenticated or anonymous?** If `user_id` is set, is it a legitimate account (possible insider or compromised credential) or a throwaway? Compromised-account path branches to identity IR.

Output of Phase 3: an actor picture — who, from where, first time or repeat, solo or campaign, authenticated or not.

---

### Phase 4 — Containment

Act on both the content and the actor. Order by reversibility — least destructive first unless active exfiltration is ongoing.

- **Session-level:** terminate the offending `session_id`. **[PRODUCTION]**
- **Actor-level:** rate-limit or block `src_ip`; revoke the `api_key_id`; disable the `user_id` if authenticated and abusive/compromised. **[PRODUCTION]**
- **Capability-level:** disable the retrieval tool or the specific data connector the injection abused, so the same attack cannot re-fetch sensitive documents while you investigate. **[PRODUCTION]**
- **Application-level:** if exfiltration is active and widespread, take the app to a safe mode (retrieval disabled) or offline. Business-impact decision — escalate to owner. **[PRODUCTION]**

Do not delete anything in containment. Preserve first (Phase 5).

---

### Phase 5 — Evidence preservation

LLM incidents require preserving **both layers**, plus state that rotates or expires.

- **Content logs:** full `prompt`, `response`, `retrieved_context` (with source doc IDs), `model_version`, `system_prompt_version`, `tool_calls` for the session and a window around it. Export to WORM/immutable storage. **[LAB-RUNNABLE]** for prompt/response.
- **Network logs / pcap:** firewall, proxy, gateway records for `src_ip` and `session_id`; pcap if TLS-inspected. **[PRODUCTION]**
- **Vector store snapshot:** capture the state of the document/vector store as it was at incident time — which documents were retrievable and their permissions. This changes as documents are added/removed, so snapshot early. **[PRODUCTION]**
- **Model + config state:** record exact `model_version`, `system_prompt_version`, guardrail/filter config, and any deployment flags. If the model or prompt is rolled after the incident, the evidentiary state is otherwise lost.
- **Identity artifacts:** `api_key_id`, `user_id`, auth logs.

Chain of custody: hash exports, record who collected what and when — standard DFIR discipline applies unchanged.

---

### Phase 6 — Eradication

Remove the cause, not just the symptom.

- **Close the injection vector.** Add input filtering (detect/neutralize override phrasing, encoded payloads) and output filtering (block responses containing sensitive patterns). The bypass succeeded because one or both were absent.
- **Fix over-permissioned retrieval.** The RAG store returned data the user should never reach. Remove sensitive documents from the retrievable corpus, or enforce per-user/entitlement filtering at retrieval time. This is usually the true root cause — the model did what it was asked; the data should not have been reachable.
- **Rotate exposed secrets.** Any credential, key, or token that appeared in output is now burned — rotate it.
- **Harden the system prompt** if it was overridden, but treat prompt hardening as defense-in-depth, not the primary fix — prompt injection is not reliably solved at the prompt layer.

---

### Phase 7 — Recovery

- Restore the app / retrieval capability with the Phase 6 controls in place.
- Validate: replay the attack (and variants) against the fixed system in a safe environment; confirm it now refuses or filters.
- Return to normal monitoring with detection sensitivity temporarily raised for this vector and this actor.
- Confirm no persistence: verify the vector store, system prompt, and connectors are clean and no attacker-supplied content remains retrievable.

---

### Phase 8 — Lessons learned

- **Feed IOCs back into detection.** Turn the confirmed attack into a new/tuned Splunk rule — the specific injection phrasing, the `tls_fingerprint`, the retrieval-volume threshold. This is the detection-engineering loop closing.
- **Preparation gaps to fix:**
  - If content and network logs could not be joined, mandate a correlatable `session_id` + `user_id` in app logging. This is the single most important preparation control for LLM IR.
  - If the vector store had no point-in-time snapshot capability, add it.
  - If sensitive documents were retrievable at all, revisit what belongs in the RAG corpus.
- **Metric honesty.** Record detection performance during the incident (did the rule catch it, or did something else?) and update `EVALUATION.md` expectations.
- **Update this playbook** with anything the response surfaced.

---

*Detection artifacts referenced: `../detect_absence_of_refusal.spl`, `../EVALUATION.md`, `../sigma/llm_absence_of_refusal.yml`. Lab data: `../datasets/daninthewild_labeled.corrected.jsonl` (content layer only). Indirect-delivery variant: `../email-prompt-injection/` (attack, dual-surface detection, Sigma port).*
