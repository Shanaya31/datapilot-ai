"""Cosine-similarity retrieval over the local knowledge index."""
from __future__ import annotations

import json
from functools import lru_cache

import numpy as np

from ..config import get_settings
from .ingest import embed_texts


@lru_cache(maxsize=1)
def _load() -> tuple[np.ndarray, list[dict]]:
    d = get_settings().index_dir
    if not (d / "kb_vectors.npy").exists():
        raise FileNotFoundError("Knowledge index missing. Run: python -m datapilot.rag.ingest")
    vectors = np.load(d / "kb_vectors.npy")
    vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors, json.loads((d / "kb_chunks.json").read_text())


def search(query: str, top_k: int = 4) -> list[dict]:
    vectors, chunks = _load()
    q = embed_texts([query], "RETRIEVAL_QUERY")[0]
    q = q / np.linalg.norm(q)
    scores = vectors @ q
    order = np.argsort(-scores)[:top_k]

    results = []
    for i in order:
        score = float(scores[i])
        if score < 0.75:
            continue

        results.append(
            {
                "source": chunks[i]["source"],
                "heading": chunks[i]["heading"],
                "text": chunks[i]["text"],
                "score": round(score, 3),
            }
        )

    return results