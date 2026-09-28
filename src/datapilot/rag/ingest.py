"""Chunk docs/knowledge/*.md by '## ' headings, embed, and save a small local vector index.

    python -m datapilot.rag.ingest

The corpus is tiny, so a numpy index is enough. Upgrade path: BigQuery VECTOR_SEARCH.
"""
from __future__ import annotations

import json
import re

import numpy as np
from google import genai
from google.genai import types

from ..config import get_settings


def chunk_markdown(text: str, source: str) -> list[dict]:
    chunks, title = [], source
    for block in re.split(r"(?m)^## ", text):
        block = block.strip()
        if not block:
            continue
        if block.startswith("# "):  # document title block before the first '## '
            title = block.splitlines()[0].lstrip("# ").strip()
            block = "\n".join(block.splitlines()[1:]).strip()
            if not block:
                continue
            heading = "Overview"
            body = block
        else:
            heading, _, body = block.partition("\n")
        chunks.append({"source": source, "doc_title": title, "heading": heading.strip(), "text": body.strip()})
    return chunks


def embed_texts(texts: list[str], task_type: str) -> np.ndarray:
    s = get_settings()
    client = genai.Client(vertexai=True, project=s.project, location=s.location)
    vectors = []
    # One request per text: Vertex's gemini-embedding-001 accepts a single input per call.
    for t in texts:
        resp = client.models.embed_content(
            model=s.embedding_model, contents=t, config=types.EmbedContentConfig(task_type=task_type)
        )
        vectors.append(resp.embeddings[0].values)
    return np.array(vectors, dtype=np.float32)


def main() -> None:
    s = get_settings()
    chunks: list[dict] = []
    for path in sorted(s.knowledge_dir.glob("*.md")):
        chunks += chunk_markdown(path.read_text(), path.name)
    print(f"Embedding {len(chunks)} chunks from {s.knowledge_dir} ...")
    vectors = embed_texts([f"{c['heading']}\n{c['text']}" for c in chunks], "RETRIEVAL_DOCUMENT")
    s.index_dir.mkdir(parents=True, exist_ok=True)
    np.save(s.index_dir / "kb_vectors.npy", vectors)
    (s.index_dir / "kb_chunks.json").write_text(json.dumps(chunks, indent=2))
    print(f"Saved index to {s.index_dir}")


if __name__ == "__main__":
    main()
