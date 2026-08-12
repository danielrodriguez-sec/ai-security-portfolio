# AI Incident Response Playbook
## Scenario 2 — Suspected Training-Data / Model Poisoning in Production

**Framework mapping:** OWASP LLM04:2025 (Data and Model Poisoning) · MITRE ATLAS AML.T0020 (Poison Training Data), AML.T0018 (Manipulate AI Model), AML.T0031 (Erode AI Model Integrity)
**Severity baseline:** High to Critical — integrity of the model itself is in question
**Applies to:** Any deployment using a fine-tuned, continually-trained, or RAG-augmented model where the training/knowledge inputs are not fully trusted.

---

### Scope note — lab vs production

Written for **production**. Tags: **[LAB-RUNNABLE]** against `index=llm_lab_corrected` (content layer only); **[PRODUCTION]** requires training pipeline, model registry, and dataset lineage the lab does not have.

Poisoning differs from the other scenarios: the attack happened **upstream and earlier** — in the data that trained or augmented the model — and only surfaces later as anomalous behavior at inference. Detection is behavioral and statistical, not a single alerting event. Assumed production telemetry adds: `training_dataset_id`, `data_source`, `ingestion_timestamp`, `model_registry_version`, `fine_tune_job_id`, and RAG document provenance (`source_doc_id`, `ingested_by`, `ingested_at`).

---

### Phase 1 — Detection signals

Poisoning rarely trips one rule. It surfaces as a pattern:

- **Behavioral drift on a specific trigger.** The model behaves normally except when a specific phrase/token appears, then produces attacker-chosen output (a backdoor). **[LAB-RUNNABLE]** to demonstrate the *shape* by grouping outputs by trigger phrase.
- **Targeted refusal collapse.** Guardrails hold generally but fail reproducibly on one topic or phrasing — consistent with poisoned alignment data.
- **Systematic factual corruption.** The model confidently emits the same wrong answer for a class of queries (e.g. always recommends one attacker product).
- **Anomaly in training inputs.** Spike in ingested records from one source, duplicated/near-duplicate samples, or label anomalies. **[PRODUCTION]** — requires dataset lineage.
- **RAG-layer poisoning.** Malicious content was ingested into the vector store and is now retrieved as authoritative. **[PRODUCTION]**

Behavioral-drift shape (content layer):

```
index=llm_lab_corrected
| eval trigger = if(match(lower(prompt), "<suspected trigger phrase>"), "trigger_present", "trigger_absent")
| eval refusal = if(match(lower(replace(output,"’","'")), "^\W*(i can't|i cannot|i'm sorry|sorry|i apologize|i refuse)"), "refusal", "comply")
| stats count by trigger, refusal
```
A large refusal→comply swing gated on the trigger is the poisoning signature.

---

### Phase 2 — Triage: content and behavior

1. **Reproduce the anomaly.** Confirm it is deterministic, not a one-off hallucination. Poisoning reproduces on the trigger; hallucination does not.
2. **Characterize the trigger.** Isolate the exact phrase/token/topic that flips behavior. Single-turn isolation (fresh context per test) to avoid conversation-history contamination.
3. **Distinguish poisoning from alternatives.** Rule out: normal hallucination, a bad system-prompt change, a model-version regression, or RAG retrieval of legitimate-but-wrong data. Poisoning is the conclusion after these are excluded, not the first assumption.
4. **Scope the behavioral blast radius.** How many query classes are affected? One narrow backdoor vs broad integrity loss changes severity dramatically.

Decision gate: **reproducible, trigger-gated, attacker-favorable behavior not explained by config/version → treat as poisoning incident, Phase 3.**

---

### Phase 3 — Triage: provenance and lineage **[PRODUCTION]**

For poisoning, "attribution" means tracing the tainted data, not (only) an IP.

1. **Identify the model artifact.** Exact `model_registry_version` / `fine_tune_job_id` exhibiting the behavior. Does a prior version lack it? That brackets *when* the taint entered.
   ```
   index=model_registry | stats earliest(_time) by model_version, fine_tune_job_id
   ```
2. **Trace the training data lineage.** Which `training_dataset_id` fed the bad version, and which `data_source`s fed that dataset? **[PRODUCTION]**
3. **Find the anomalous ingestion.** Spike, new source, or unusual `ingested_by` around the bracketed window.
   ```
   index=training_pipeline earliest=<version_n-1_time> latest=<version_n_time>
   | stats count dc(data_source) by data_source, ingested_by
   ```
4. **For RAG poisoning:** identify the malicious `source_doc_id`(s), who ingested them (`ingested_by`), from what `src_ip`, and when. This *does* pivot to network attribution like Scenario 1 — the poisoning was a document-upload action.
5. **Insider vs external.** Was the tainted data introduced via a compromised pipeline credential, a malicious insider, or an unvetted public data source? Branches the response.

Output: the tainted artifact, the tainted data, the ingestion event, and the actor/source behind it.

---

### Phase 4 — Containment

- **Roll back the model.** Revert production to the last known-good `model_version` (the version that predates the trigger behavior). Fastest containment, usually reversible. **[PRODUCTION]**
- **Quarantine the tainted artifact** in the registry so it cannot be redeployed. **[PRODUCTION]**
- **RAG poisoning:** remove the malicious `source_doc_id`(s) from the retrievable store immediately; freeze ingestion from the implicated source. **[PRODUCTION]**
- **Freeze the training pipeline** if an active poisoning source is still feeding it — stop the bleeding before it taints the next model. **[PRODUCTION]**
- **Revoke** the pipeline credential / account used for malicious ingestion. **[PRODUCTION]**

Preserve before removing (Phase 5) — including the poisoned model itself.

---

### Phase 5 — Evidence preservation

- **The poisoned model artifact.** Preserve a copy of the tainted `model_version` — it is the primary evidence and is needed for analysis and any attribution. Do not simply delete on rollback.
- **Training dataset + lineage.** Snapshot the `training_dataset_id`, the implicated `data_source`, and ingestion logs (`ingested_by`, `ingested_at`, `src_ip`).
- **RAG:** preserve the malicious documents and their ingestion records before removal.
- **Reproduction record.** Save the exact trigger prompts and outputs demonstrating the backdoor — this is how you prove the incident.
- **Registry + pipeline config** at incident time.

Hash and log all artifacts; chain of custody as standard.

---

### Phase 6 — Eradication

- **Remove tainted data at source.** Purge poisoned samples/documents from datasets and stores so a retrain cannot re-ingest them.
- **Retrain or re-fine-tune** from clean, verified data to produce an uncompromised model version. Rollback is containment; a clean rebuild is eradication.
- **Fix the ingestion weakness.** Add provenance validation, source allow-listing, anomaly detection on training inputs, and human review for high-trust data. Poisoning succeeded because untrusted data reached training/retrieval without sufficient vetting.
- **Close the access path** (compromised credential, unvetted source, insider) identified in Phase 3.

---

### Phase 7 — Recovery

- Deploy the clean, retrained model version.
- Validate: confirm the trigger no longer produces attacker output, and that general capability did not regress (guard against over-correction).
- Monitor the previously affected query classes with heightened sensitivity.
- Verify pipeline integrity end-to-end before re-enabling automated ingestion.

---

### Phase 8 — Lessons learned

- **Detection loop:** build ongoing behavioral canaries — a fixed battery of trigger/topic probes run against each model version pre-deployment to catch backdoors before production. Turn this incident's trigger into a permanent regression test.
- **Preparation gaps:**
  - Mandate dataset lineage / provenance for every training input — without it, Phase 3 is impossible.
  - Add model-registry versioning with fast rollback if absent.
  - Vet and allow-list RAG ingestion sources.
- **Supply-chain framing.** Treat training data and RAG corpora as a software supply chain — same trust, validation, and provenance discipline.
- **Update this playbook.**

---

*Note: poisoning is the hardest LLM incident to detect and the slowest to surface. The strongest control is preventive — provenance and pre-deployment behavioral testing — because post-hoc detection depends on noticing subtle, trigger-gated drift.*
