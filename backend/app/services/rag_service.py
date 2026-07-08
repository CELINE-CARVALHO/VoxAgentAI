"""
Lightweight retrieval used to ground Gemini's responses in the uploaded
knowledge base. This is intentionally simple (keyword/overlap scoring over
chunked document text) rather than a vector DB — swap in pgvector/embeddings
later without changing the router/service call sites.
"""
import re
from typing import List

from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeDocument

CHUNK_SIZE = 800  # characters per chunk
TOP_K = 3


def _chunk(text: str, size: int = CHUNK_SIZE) -> List[str]:
    text = re.sub(r"\s+", " ", text).strip()
    return [text[i:i + size] for i in range(0, len(text), size)] if text else []


def _score(query: str, chunk: str) -> int:
    query_terms = set(re.findall(r"\w+", query.lower()))
    chunk_terms = set(re.findall(r"\w+", chunk.lower()))
    return len(query_terms & chunk_terms)


def retrieve_context(db: Session, query: str, top_k: int = TOP_K) -> str:
    """Returns the top-k most relevant chunks across all *ready* documents, concatenated."""
    docs = (
        db.query(KnowledgeDocument)
        .filter(KnowledgeDocument.status == "ready")
        .all()
    )

    scored_chunks = []
    for doc in docs:
        for chunk in _chunk(doc.content_text or ""):
            score = _score(query, chunk)
            if score > 0:
                scored_chunks.append((score, doc.filename, chunk))

    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    top = scored_chunks[:top_k]

    if not top:
        return ""

    return "\n\n".join(f"[Source: {name}]\n{chunk}" for _, name, chunk in top)