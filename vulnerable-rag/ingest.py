#!/usr/bin/env python3
"""
ingest.py — build the ChromaDB vector store for the vulnerable RAG lab app.

Reads every file in ./documents, chunks it, embeds it with Ollama's
nomic-embed-text model, and stores it in a persistent ChromaDB collection.

*** INTENTIONALLY VULNERABLE — LAB USE ONLY. ***
Deliberate flaw baked in here: sensitive and public documents are loaded into a
SINGLE collection with NO access-control boundary. Every chunk, including
confidential salary/PII/credential data, is retrievable by any query. This is
the over-permissioned-retrieval root cause exercised by the IR playbook.

Prereqs:
    ollama pull nomic-embed-text
    pip install chromadb requests

Usage:
    python3 ingest.py
"""

import os
import glob
import chromadb
from chromadb.utils import embedding_functions

DOCS_DIR = os.path.join(os.path.dirname(__file__), "documents")
STORE_DIR = os.path.join(os.path.dirname(__file__), "chroma_store")
COLLECTION = "company_docs"
OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"

# Filenames whose contents are confidential. Recorded as metadata only — the app
# does NOT filter on it (that is the point). A secure design would refuse to
# retrieve or return confidential chunks without authorization.
CONFIDENTIAL = {"internal_salaries.txt", "customer_pii.csv", "engineering_notes.txt"}


def chunk(text, source):
    """Naive chunking: CSV by row, text by paragraph. Adequate for a lab."""
    if source.endswith(".csv"):
        return [ln for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def main():
    ef = embedding_functions.OllamaEmbeddingFunction(url=OLLAMA_URL, model_name=EMBED_MODEL)
    client = chromadb.PersistentClient(path=STORE_DIR)

    # rebuild cleanly each run
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    col = client.create_collection(COLLECTION, embedding_function=ef)

    ids, docs, metas = [], [], []
    for path in sorted(glob.glob(os.path.join(DOCS_DIR, "*"))):
        source = os.path.basename(path)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        sensitivity = "confidential" if source in CONFIDENTIAL else "public"
        for i, c in enumerate(chunk(text, source)):
            ids.append(f"{source}:{i}")
            docs.append(c)
            metas.append({"source": source, "sensitivity": sensitivity})

    col.add(ids=ids, documents=docs, metadatas=metas)
    pub = sum(1 for m in metas if m["sensitivity"] == "public")
    conf = sum(1 for m in metas if m["sensitivity"] == "confidential")
    print(f"ingested {len(ids)} chunks into '{COLLECTION}' "
          f"({pub} public, {conf} confidential) at {STORE_DIR}")
    print("WARNING: confidential chunks are retrievable with no access control (by design).")


if __name__ == "__main__":
    main()
