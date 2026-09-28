"""Tool for the Knowledge Agent."""
from __future__ import annotations

from ..rag.retriever import search


def search_knowledge_base(query: str, top_k: int = 4) -> dict:
    """Search pipeline documentation, SOPs, data-quality rules and troubleshooting guides.

    Args:
        query: Natural-language query, e.g. "NULL spike in customer_id runbook".
        top_k: Number of passages to return (1-6).
    """
    try:
        return {"passages": search(query, top_k=max(1, min(int(top_k), 6)))}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}
