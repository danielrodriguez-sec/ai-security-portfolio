# AI Incident Response Playbook

Operational IR playbooks for AI/LLM security incidents, structured the way a SOC
would actually run them — detection through containment to lessons learned. This
is the response half of the portfolio; the detection half lives in
`../splunk-detection-pack/`, and each playbook's detection-signal phase points
back at those rules.

## Scope — production playbook, lab-validated where possible

These playbooks are written for a **production** LLM deployment. The lab has no
running LLM application and collects no network logs, so every search is tagged:

- **[LAB-RUNNABLE]** — runs against the lab dataset (`index=llm_lab_corrected`,
  the DanInTheWild content layer: prompt + response). These are demonstrated, not
  hypothetical.
- **[PRODUCTION]** — requires telemetry a real deployment has (gateway/firewall
  logs, session identity, vector store, IAM, downstream systems). Written as the
  query you would run, explicitly not runnable in the lab.

This separation is deliberate: it shows the full production process while being
honest about what the lab environment can and cannot demonstrate.

## Assumed production log schema

**LLM application event (content layer):** `timestamp, session_id, user_id,
prompt, retrieved_context, response, model_version, tool_calls, tokens_in,
tokens_out, latency_ms, system_prompt_version`.

**Gateway / proxy / firewall event (network layer), joined on `session_id` /
`user_id`:** `src_ip, geo, asn, user_agent, tls_fingerprint, auth_method,
api_key_id`, request volume/timing.

**Join key:** `session_id` (and `user_id` when authenticated). Correlating the
content layer (what happened) with the network layer (who, from where) depends on
the app logging a correlatable identity. Where it doesn't, attribution is
impossible — a preparation-phase requirement every playbook calls out.

## Common structure (all scenarios)

1. Detection signals
2. Triage — content
3. Triage — network attribution & provenance
4. Containment
5. Evidence preservation
6. Eradication
7. Recovery
8. Lessons learned

## Scenarios

| # | Scenario | Primary OWASP / ATLAS | Defining challenge |
|---|----------|-----------------------|--------------------|
| 1 | [Prompt injection → RAG data exfiltration](scenario-1-rag-data-exfiltration.md) | LLM01, LLM02 / AML.T0051.000, T0057 | Content + network join; over-permissioned retrieval |
| 2 | [Training-data / model poisoning](scenario-2-training-data-poisoning.md) | LLM04 / AML.T0020, T0018 | Upstream, delayed, behavioral; data lineage |
| 3 | [Model output causing downstream harm](scenario-3-harmful-output.md) | LLM05, LLM09 / AML.T0048 | Trust boundary between output and action |
| 4 | [Credential / API-key leakage via output](scenario-4-credential-leakage.md) | LLM02, LLM06 / AML.T0057, T0055 | Dual-clock: rotate before full analysis |
| 5 | [Jailbreak-as-a-service abuse](scenario-5-jailbreak-as-a-service.md) | LLM01, LLM10 / AML.T0054, T0034 | Distributed, economic; campaign attribution |

## How this connects to the detection pack

Each scenario's Phase 1 references concrete detections from
`../splunk-detection-pack/` — the absence-of-refusal SPL rule, its evaluation,
and the Sigma port. Phase 8 (lessons learned) closes the loop: confirmed
incidents produce new detection content. The two projects are the two halves of
the same operational cycle.

## Method notes

- Frameworks: OWASP LLM Top 10 (2025), MITRE ATLAS.
- The lab dataset is the corrected DanInTheWild corpus
  (`../splunk-detection-pack/datasets/daninthewild_labeled.corrected.jsonl`),
  content layer only.
- Detection performance is treated honestly throughout: keyword detection scores
  precision 0.725 / recall 0.812 against corrected ground truth, and playbooks
  reference that limitation rather than assuming detections are perfect.
