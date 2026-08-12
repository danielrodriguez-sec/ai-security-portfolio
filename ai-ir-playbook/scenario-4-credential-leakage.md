# AI Incident Response Playbook
## Scenario 4 — Credential or API-Key Leakage Through Model Output

**Framework mapping:** OWASP LLM02:2025 (Sensitive Information Disclosure), LLM06:2025 (Excessive Agency where keys grant access) · MITRE ATLAS AML.T0057 (LLM Data Leakage), AML.T0055 (Unsecured Credentials)
**Severity baseline:** High to Critical — a leaked live credential is an active access path
**Applies to:** Any deployment where secrets could reach the model's context — via system prompt, RAG documents, tool outputs, conversation history, or training data.

---

### Scope note — lab vs production

Written for **production**. Tags: **[LAB-RUNNABLE]** against `index=llm_lab_corrected` (response content); **[PRODUCTION]** requires secret-management, IAM, and downstream-access logs the lab does not have.

Distinguishing feature: the leaked secret is a **live access path**, so this scenario runs on **two clocks** — the LLM incident *and* a credential-compromise incident that starts the moment the key is exposed. Containment (rotate the key) often must happen before full analysis. Assumed production telemetry adds: `api_key_id`, `secret_ref`, IAM/access logs for the leaked credential's scope.

---

### Phase 1 — Detection signals

- **Secret pattern in model output.** Response contains something shaped like a credential — API key, token, connection string, private key, password. **[LAB-RUNNABLE]** to scan `output`.
- **System-prompt / context leak.** Model reveals its system prompt or injected context, which contained secrets. **[LAB-RUNNABLE]**
- **Secret scanner hit on AI logs.** A secret-scanning tool flags the LLM log stream itself (the secret is now sitting in your logs — a second exposure).
- **Downstream anomalous auth.** Use of the leaked credential from an unexpected source after the leak. **[PRODUCTION]** — IAM logs.

High-signal secret detection (content layer):

```
index=llm_lab_corrected
| eval secret_hit = case(
    match(output, "AKIA[0-9A-Z]{16}"), "aws_key",
    match(output, "(?i)sk-[a-zA-Z0-9]{20,}"), "openai_key",
    match(output, "ghp_[A-Za-z0-9]{36}"), "github_pat",
    match(output, "-----BEGIN (RSA|OPENSSH|PRIVATE) KEY-----"), "private_key",
    match(output, "(?i)(password|passwd|pwd)\s*[:=]\s*\S+"), "password",
    match(output, "(?i)(postgres|mysql|mongodb)://[^:\s]+:[^@\s]+@"), "conn_string",
    1=1, "none")
| where secret_hit != "none"
| table _time, session_id, secret_hit, output
```

---

### Phase 2 — Triage: confirm and classify the secret

Speed matters — a live credential is being exposed each second it remains valid.

1. **Confirm it is a real secret**, not a placeholder/example (`sk-xxxx`, `password=example`). False positives are common in this class.
2. **Identify what it grants.** What system, what scope, what privilege? A read-only sandbox key is low; a production cloud admin key is critical. This sets severity and the second clock's urgency.
3. **Determine if it is live.** Is the credential currently valid? If yes → the credential-compromise clock is running; proceed to rotate (Phase 4) in parallel with the rest of triage.
4. **Find the exposure source — how did a secret reach the model?**
   - system prompt containing a secret,
   - a RAG document with an embedded credential,
   - a tool/function output returned into context,
   - conversation history,
   - training data.
   This determines eradication.

Decision gate: **real + live credential → dual incident (LLM leak + credential compromise); rotate immediately, do not wait for full analysis.**

---

### Phase 3 — Triage: exposure scope and access forensics **[PRODUCTION]**

Two questions: who *received* the leak, and was the credential *used*.

1. **Who received the secret.** All sessions/users whose responses contained it — the leak may have been served to many. Pivot on the pattern across the population.
   ```
   index=llm_app | where match(output, "<secret pattern>") | stats dc(session_id) values(user_id) by _time
   ```
2. **Requester context.** For each recipient: `src_ip`, geo/ASN, auth identity, history — as Scenario 1. Distinguish an attacker who extracted it deliberately from a user who received it incidentally.
3. **Was the credential used?** The critical forensic question. Pull IAM/access logs for the leaked `api_key_id`/`secret_ref`: any authentication events, especially from new IPs/geos, after the exposure time.
   ```
   index=iam credential_id="<leaked>" earliest=<leak_time>
   | iplocation src_ip | stats count by src_ip, Country, action, status
   ```
4. **Establish exposure window.** First moment the secret appeared in output → moment of rotation. Everything the credential could touch in that window is in scope.

---

### Phase 4 — Containment

**Rotate first.** Unlike other scenarios, containment leads.

- **Rotate/revoke the leaked credential immediately.** This neutralizes the access path and is the single most important action. Do it before full analysis if the credential is live and privileged. **[PRODUCTION]**
- **Revoke downstream sessions/tokens** the credential may have established. **[PRODUCTION]**
- **Purge the secret from the LLM logs / conversation stores** where it is now sitting (a live secret in searchable logs is ongoing exposure) — but preserve an evidentiary copy in access-controlled storage first (Phase 5). **[PRODUCTION]**
- **Block the exposure path in the running app:** output filter for the secret pattern, and disable the specific source (RAG doc, tool) leaking it. **[PRODUCTION]**
- **If the credential was used maliciously,** trigger the downstream system's own IR for that access.

---

### Phase 5 — Evidence preservation

- **The leaking output(s)** — `prompt`, `response`, `session_id`, `model_version`, `system_prompt_version` — in access-controlled storage (the evidence itself contains a secret; handle accordingly). **[LAB-RUNNABLE]** for prompt/response.
- **The exposure source:** the system prompt / RAG doc / tool output / training record that carried the secret.
- **IAM/access logs** for the leaked credential across the exposure window — proves used-or-not. **[PRODUCTION]**
- **Recipient list:** sessions/users served the secret.
- **Rotation record:** when the credential was rotated, by whom.
- Hash and log; restrict access to these artifacts more tightly than normal (they contain live-until-rotated secrets).

---

### Phase 6 — Eradication

- **Remove the secret from the model's reachable context at the source:**
  - secret in system prompt → move to a secure secret store, referenced not embedded;
  - secret in RAG corpus → remove the document, scan the corpus for others;
  - secret in tool output → stop the tool from returning raw secrets into context;
  - secret in training data → purge and plan retrain (see Scenario 2).
- **Add secret-scanning to two places:** ingestion (block secrets entering context/training) and output (block secrets leaving). Defense on both sides.
- **Adopt secret-reference patterns** so raw credentials never enter the model's context in the first place — the durable fix.
- **Enforce least privilege** on any credential that must exist near the system, limiting blast radius of the next leak.

---

### Phase 7 — Recovery

- Confirm the rotated credential is deployed to legitimate consumers and the old one is fully dead.
- Re-enable the app with ingestion + output secret-scanning active.
- Validate: attempt to elicit the secret again; confirm it is now absent from context and/or filtered from output.
- Monitor IAM logs for any late attempts to use the dead credential (indicates who captured it).

---

### Phase 8 — Lessons learned

- **Detection loop:** deploy standing secret-detection on the LLM output stream and the log stream; alert on any secret pattern in model I/O.
- **Preparation gaps:**
  - Audit everything that enters model context (system prompt, RAG, tools, history) for secrets — this leak means the pipeline allows it.
  - Move all secrets to a managed store with reference-based access; ban embedded credentials.
  - Ensure LLM logs are themselves secret-scanned and access-controlled, so logging does not become a second exposure.
- **Blast-radius reduction:** least-privilege every credential in reach of the model.
- **Update this playbook.**

---

*Dual-clock reminder: treat every confirmed live-credential leak as simultaneously an LLM incident and a credential-compromise incident. The rotation clock starts at exposure, not at detection — minimize the gap.*
