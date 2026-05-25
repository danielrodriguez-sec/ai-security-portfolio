# AI Security Frameworks: A Practitioner's Cross-Reference

**OWASP Top 10 for LLM Applications (2025) → MITRE ATLAS → NIST AI RMF 1.0**
**With analyst observables and IR evidence-preservation guidance.**

This document maps the three frameworks an AI security analyst will actually use day-to-day, then bridges them to two things the framework documents themselves don't cover: what an analyst *sees* in their telemetry when each risk materializes, and what evidence they need to preserve for incident response.

The goal is an operational reference, not a compliance crosswalk. Every row should answer four questions: *what is the risk, what technique implements it, what governance outcome does it threaten, and what does my SOC do about it?*

**Sources.**
- OWASP Top 10 for LLM Applications v2.0 (2025) — released Nov 2024.
- MITRE ATLAS — IDs and names verified against `ATLAS.yaml` v5.6.0 from the `mitre-atlas/atlas-data` GitHub repository.
- NIST AI RMF 1.0 (NIST AI 100-1, Jan 2023) — subcategory IDs and text verified against `airc.nist.gov`.

**Scope note.** OWASP entries are 1-to-1. ATLAS techniques are listed where the mapping is direct; an OWASP risk often manifests through multiple ATLAS techniques, and the most representative ones are listed first. NIST AI RMF subcategories are the *primary* outcomes affected — not exhaustive. ATLAS adds techniques regularly; verify IDs against `atlas.mitre.org` if reusing this in production documentation.

---

## Primary Mapping

| OWASP LLM 2025 | Primary MITRE ATLAS Technique(s) | NIST AI RMF Subcategory | What the Analyst Sees | Evidence to Preserve |
|---|---|---|---|---|
| **LLM01:2025 Prompt Injection** | `AML.T0051` LLM Prompt Injection (sub: `.000` Direct, `.001` Indirect, `.002` Triggered); `AML.T0054` LLM Jailbreak; `AML.T0093` Prompt Infiltration via Public-Facing Application | `MAP-5.1`, `MEASURE-2.7`, `MANAGE-4.1` | Inputs containing instruction-override patterns ("ignore previous", role-play scaffolds), encoded payloads (base64, leetspeak, zero-width chars), unexpected system-prompt-shaped output, sudden topic shifts mid-session. For indirect: model behavior changing right after a tool/retrieval call. | Full prompt (system + user + any injected context), retrieved RAG chunks with source URIs, complete model output, tool-call trace, session ID, upstream source content if indirect, timestamps with sub-second precision. |
| **LLM02:2025 Sensitive Information Disclosure** | `AML.T0024` Exfiltration via AI Inference API (sub: `.000` Infer Training Data Membership, `.001` Invert AI Model); `AML.T0057` LLM Data Leakage | `GOVERN-1.1`, `MAP-4.1`, `MEASURE-2.10`, `MANAGE-2.3` | Model outputs containing PII patterns (SSNs, card numbers, email lists), API keys or tokens, internal hostnames, verbatim training-data fragments, or RAG documents the user shouldn't have access to. Often paired with repeated probing queries. | Output logs with PII pre-redaction copy preserved in legal-hold storage, query history for the session, embedding-store snapshot, retrieval logs showing which documents were pulled, downstream destination of the leaked data if exfiltrated further. |
| **LLM03:2025 Supply Chain** | `AML.T0010` AI Supply Chain Compromise (sub: `.000` Hardware, `.001` AI Software, `.002` Data, `.003` Model, `.004` Container Registry, `.005` AI Agent Tool); `AML.T0019` Publish Poisoned Datasets; `AML.T0058` Publish Poisoned Models; `AML.T0109` AI Supply Chain Rug Pull | `GOVERN-1.4`, `GOVERN-6.1`, `MAP-4.1`, `MANAGE-3.1` | Pulls from unverified model hubs, hash mismatches against known-good baselines, unexpected new dependencies in ML framework versions, model files containing executable payloads (pickle exploits, suspicious TorchScript ops), legitimate components that turn malicious after an update (rug-pull pattern). | Model file hash (SHA-256), source registry URL and pull timestamp, full dependency tree (`pip freeze` / lockfile), SBOM, signature/provenance metadata if any, version history of the artifact, any pre-flight scan results (ModelScan, picklescan, etc.). |
| **LLM04:2025 Data and Model Poisoning** | `AML.T0020` Poison Training Data; `AML.T0018` Manipulate AI Model (sub: `.000` Poison AI Model, `.001` Modify AI Model Architecture, `.002` Embed Malware); `AML.T0031` Erode AI Model Integrity; `AML.T0059` Erode Dataset Integrity | `MAP-2.3`, `MEASURE-2.7`, `MEASURE-2.11`, `MANAGE-2.3` | Sudden accuracy/behavior drift after retraining, biased outputs on specific inputs only, model responding correctly *except* for a narrow trigger phrase, gradual quality erosion in production metrics. | Training dataset snapshot at the suspect version, dataset diff against last known-good, model artifact (before and after), training run logs, data ingestion source manifest, eval-set results across versions. |
| **LLM05:2025 Improper Output Handling** | `AML.T0050` Command and Scripting Interpreter (downstream consequence); `AML.T0067` LLM Trusted Output Components Manipulation (sub: `.000` Citations); `AML.T0077` LLM Response Rendering; `AML.T0051.001` LLM Prompt Injection: Indirect (typical upstream cause) | `MAP-5.1`, `MEASURE-2.7`, `MANAGE-2.4` | LLM-generated content executed downstream: SQL run against a DB, shell commands executed, HTML rendered with script tags, markdown links pointing to attacker domains. SSRF or XSS patterns originating from model output. Hidden content visible to the model but rendered invisibly to the user. | Model output verbatim (pre-rendering), the downstream system's execution log (DB query log, shell history, web server log), the user input that produced the output, the system-prompt template that was supposed to constrain output format, the rendered client view if available. |
| **LLM06:2025 Excessive Agency** | `AML.T0053` AI Agent Tool Invocation; `AML.T0086` Exfiltration via AI Agent Tool Invocation; `AML.T0101` Data Destruction via AI Agent Tool Invocation; `AML.T0061` LLM Prompt Self-Replication | `GOVERN-1.5`, `MAP-3.5`, `MANAGE-1.3`, `MANAGE-2.4` | Agent invoking tools the user did not request, chained tool calls without human checkpoints, off-hours activity from agent service accounts, plugins called with arguments the user never typed, write/delete actions against systems the agent shouldn't reach. | Full agent action log (every tool call with arguments and return values), reasoning trace if available, OAuth/API tokens used by the agent, IAM-level audit log of resources touched, user's original request alongside what the agent actually did. |
| **LLM07:2025 System Prompt Leakage** | `AML.T0056` Extract LLM System Prompt; `AML.T0069` Discover LLM System Information (sub: `.002` System Prompt); `AML.T0051` LLM Prompt Injection (typical delivery mechanism) | `GOVERN-1.4`, `MAP-4.1`, `MEASURE-2.10` | Output containing strings recognizable as system-prompt scaffolding ("You are...", role definitions, tool schemas, internal instructions), or output revealing guardrail rules, secret keys, or backend identifiers that should have been hidden. | The leaked output, the system prompt that was supposed to be hidden, the eliciting user input, session history showing the extraction sequence, any secrets the system prompt should not have contained (this is a governance finding, not just an IR finding). |
| **LLM08:2025 Vector and Embedding Weaknesses** | `AML.T0070` RAG Poisoning; `AML.T0066` Retrieval Content Crafting; `AML.T0082` RAG Credential Harvesting; `AML.T0085` Data from AI Services (sub: `.000` RAG Databases); `AML.T0071` False RAG Entry Injection | `MAP-2.3`, `MAP-4.1`, `MEASURE-2.10`, `MANAGE-2.3` | RAG retrieving documents the user shouldn't have access to (cross-tenant leakage), poisoned documents in the corpus surfacing in retrievals, embedding inversion attacks reconstructing source text, identical/near-identical embeddings indicating injected poison vectors. | Vector store snapshot, retrieval logs (query + returned chunks + similarity scores), access control state for the corpus at incident time, source document metadata, embedding model version, ingestion pipeline logs. |
| **LLM09:2025 Misinformation** | `AML.T0048` External Harms (sub: `.000`–`.004` financial, reputational, societal, user, IP); `AML.T0060` Publish Hallucinated Entities; `AML.T0062` Discover LLM Hallucinations; `AML.T0100` AI Agent Clickbait | `GOVERN-1.2`, `MAP-3.1`, `MEASURE-2.5`, `MEASURE-2.9` | Hallucinated facts being trusted by operators, fabricated citations, invented API endpoints in generated code (slopsquatting), confident-but-wrong outputs that downstream systems acted on. Often surfaces as a *business* incident before a security one. | The output that caused harm, the downstream action taken on it (committed code, sent email, executed trade), the user's apparent reliance level, model version and config, any guardrail/grounding signals that fired or should have. |
| **LLM10:2025 Unbounded Consumption** | `AML.T0029` Denial of AI Service; `AML.T0034` Cost Harvesting (sub: `.000` Excessive Queries, `.001` Resource-Intensive Queries, `.002` Agentic Resource Consumption); `AML.T0044` Full AI Model Access; `AML.T0024.002` Extract AI Model | `GOVERN-1.5`, `MAP-3.5`, `MEASURE-2.7`, `MANAGE-3.1` | Token-rate spikes, recursive or self-amplifying prompts, GPU saturation, API quota burn, sustained high-volume querying from a small number of accounts, model-extraction patterns (high-volume systematic probing). | Per-account token/request counters at incident-window resolution, billing telemetry, rate-limit log, request payload samples, source IP/account, any rate-limiter or WAF decisions, cost delta against baseline. |

---

## Mapping Notes

**ATLAS technique IDs change.** ATLAS is updated regularly; the IDs above were verified against `ATLAS.yaml` v5.6.0 (May 2026) from `mitre-atlas/atlas-data`, which contains 16 tactics and 170 techniques and sub-techniques. Re-check IDs at `atlas.mitre.org` before using this in production documentation.

**OWASP-to-ATLAS is not 1-to-1.** Several OWASP entries (notably LLM01, LLM05, LLM08) share upstream ATLAS techniques because they describe related stages of the same attack chain. The mapping above lists the *most representative* ATLAS techniques for each OWASP entry; in a real incident, expect to cite multiple. Many of the new (2025–2026) ATLAS additions are agent- and RAG-specific (`T0070`–`T0112`) — when threat-modeling agent or RAG systems, search ATLAS for those ranges first.

**NIST AI RMF is a governance framework, not a technical taxonomy.** The subcategories listed are the outcomes most directly threatened — they're useful for talking to GRC, audit, and leadership about *why* a finding matters, not for technical detection. `GOVERN` outcomes apply organization-wide; `MAP/MEASURE/MANAGE` outcomes apply per AI system.

**The "Insecure Plugin Design" entry is gone.** If you see it cited in older content (it was `LLM07:2023`), most of its substance moved into `LLM06:2025 Excessive Agency`. Similarly, "Insecure Output Handling" was renamed to "Improper Output Handling," "Training Data Poisoning" was broadened to "Data and Model Poisoning," "Overreliance" became "Misinformation," and "Model DoS" became "Unbounded Consumption." Two new entries — System Prompt Leakage and Vector and Embedding Weaknesses — were added.

---

## High-Value Detection Indicators

These are the observable patterns most worth building detections against. Each maps back to the table above.

### Prompt Injection Indicators *(LLM01, LLM07 · `AML.T0051`, `AML.T0054`, `AML.T0056`)*

| Indicator | Analyst Observation |
|---|---|
| Instruction override attempts | Prompts containing "ignore", "disregard", "you are now", "system:" headers in user content |
| Unicode / encoding obfuscation | Zero-width chars, base64 blobs, leetspeak, homoglyphs, RTL overrides in inputs (see `AML.T0068` LLM Prompt Obfuscation) |
| Embedded hidden prompts | Instruction-like text inside HTML, PDFs, markdown, image alt text, OCR'd content |
| System prompt extraction | Inputs asking the model to repeat, summarize, or translate its instructions |
| Recursive prompt chaining | Multi-turn sequences building toward an extraction or jailbreak goal |
| Jailbreak persona scaffolds | Role-play setups (DAN, evil twin, hypothetical-character framings) |
| Delayed-execution triggers | Instructions that activate on a future condition (see `AML.T0094` Delay Execution of LLM Instructions) |

### Sensitive Data Leakage Indicators *(LLM02, LLM07, LLM08 · `AML.T0024`, `AML.T0057`, `AML.T0082`)*

| Indicator | Analyst Observation |
|---|---|
| Secrets in output | API keys, tokens, connection strings appearing in model responses |
| Internal document leakage | Confidential business content surfacing in answers to broad queries |
| PII disclosure | SSNs, card numbers, customer records appearing where they shouldn't |
| Embedding inversion / leakage | Source text being reconstructed from vector representations (`AML.T0024.001`) |
| Training data membership | Probing patterns testing whether specific data was in training set (`AML.T0024.000`) |
| Repeated extraction attempts | Systematic probing of memorized training data or RAG corpus |
| Cross-tenant retrieval | RAG returning chunks from another customer's documents |

### AI Supply Chain Indicators *(LLM03, LLM04 · `AML.T0010`, `AML.T0019`, `AML.T0020`, `AML.T0058`, `AML.T0109`)*

| Indicator | Analyst Observation |
|---|---|
| Unverified model downloads | Pulls from non-allowlisted hubs, missing signatures, hash mismatches |
| Dependency tampering | New or modified ML framework versions; unexpected transitive packages |
| Unexpected model drift | Sudden accuracy or behavior changes against the eval baseline |
| Tokenizer / parsing anomalies | Inputs producing unexpected tokenization or vocab-out-of-range events |
| Unauthorized retraining | Fine-tuning or RAG-ingestion events outside change-control |
| Malicious model artifacts | Pickle exploits, suspicious TorchScript ops, oversized embedded payloads |
| Rug-pull update | A previously-trusted artifact ships a malicious update post-adoption (`AML.T0109`) |

### Agent Abuse Indicators *(LLM06, LLM10 · `AML.T0053`, `AML.T0086`, `AML.T0061`, `AML.T0080`, `AML.T0110`)*

| Indicator | Analyst Observation |
|---|---|
| Excessive tool invocation | Repeated plugin/API calls beyond what the task requires |
| Recursive autonomous loops | Self-triggering workflows; agents calling themselves through tools |
| Unauthorized external actions | Unexpected emails sent, purchases made, infrastructure modified |
| Off-hours agent activity | Agent service accounts active outside normal user windows |
| Unexpected network egress | Connections to domains the agent has never reached before |
| Privilege boundary crossing | Agent accessing resources beyond the invoking user's role |
| Persistent context contamination | Behavior changes across sessions from poisoned memory/thread (`AML.T0080`) |
| Agent tool poisoning | A previously-trusted tool returns malicious content (`AML.T0099`, `AML.T0110`) |

---

## Recommended AI SOC Monitoring Priorities

Order matters here — top items are foundational and unlock the ones below them.

1. **Prompt and response logging** — without this, no other AI-specific detection is possible. Logs must capture system + user prompts, retrieved context, full output, tool calls, session ID, and timestamps. Covers detection for nearly every LLM0x entry.
2. **Agent action auditing** — every tool call with arguments, return values, and the IAM context used. Foundational for `LLM06` and any post-incident reconstruction of agent behavior.
3. **LLM API anomaly detection** — per-account, per-endpoint baselines for request rate, prompt length, output length, error rate. Catches `LLM10` and most automated probing.
4. **Token consumption monitoring** — independent of #3 because cost-based signals can fire before behavioral ones; ties to `LLM10` and to early detection of `LLM01` recursion attacks.
5. **Model integrity verification** — hash and signature checks at load time; eval-suite regression checks on every model version. Catches `LLM03` and `LLM04`.
6. **RAG access logging** — query, retrieved chunks, similarity scores, access-control decision. Essential for `LLM02` and `LLM08`.
7. **Plugin / tool permission segmentation** — each agent capability gated by a distinct minimal-scope credential. A preventive control more than a detection, but the audit trail it produces is what makes `LLM06` incidents reconstructable.
8. **AI-specific DLP** — outbound content inspection tuned to detect secrets, PII, and embeddings in model output. Last line of defense for `LLM02` when upstream controls fail.
9. **Human approval checkpoints** — high-impact agent actions (writes, sends, payments, infra changes) require a human in the loop. The log of approve/deny decisions is itself high-signal telemetry.
10. **Continuous adversarial red-team testing** — scheduled Garak / PyRIT / internal-team runs against production model versions. The findings populate detection content for everything above.

---

## A Note on How AI Incidents Differ

AI incident response includes everything traditional IR covers — the AI system still runs on infrastructure, still uses credentials, still gets phished, still has lateral-movement risk — *plus* a class of failure modes the traditional toolchain doesn't see:

- **Prompt injection** as both initial access and execution
- **Model manipulation** (poisoning, backdoors, integrity erosion)
- **Autonomous agent misuse** (tool chaining, self-replication, off-policy actions)
- **Embedding and RAG leakage** (cross-tenant, training-data extraction)
- **Inference-time exfiltration** (model extraction, API-based data leakage)
- **Hallucination-driven downstream harm** (the system worked exactly as designed and still caused damage)
- **AI supply chain compromise** (model artifacts, datasets, ML frameworks, agent tools)

The operational tell that distinguishes an AI incident from a conventional one is that the *first* signal is usually framed as **"unexpected or abnormal model behavior"** rather than as obvious malicious activity. Triage starts with treating that signal as a security event rather than an ML quality issue — and that's the analyst judgment call AI SOC roles are hiring for.

---

*Daniel Rodriguez — `ai-security-portfolio`*
*Cross-references: `splunk-detection-pack/`, `ai-ir-playbook/`*
