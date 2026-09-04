"""
Retrieval-Augmented Generation (RAG) service for VoxAgent AI.

Embeds document chunks with sentence-transformers (all-MiniLM-L6-v2 by default),
stores them in a Pinecone serverless index (free tier compatible), and retrieves
relevant context via cosine-similarity search.

Public API — the same interface the rest of the app already uses:

    retrieve_context(db, query, top_k)  ->  str   (formatted context string)

New indexing helpers (called by crud/knowledge.py and routers/knowledge.py):

    index_document(doc_id, filename, content_text)
    delete_document_vectors(doc_id)

Falls back to the original TF-IDF ranker when Pinecone is not configured
(PINECONE_API_KEY is empty), so the app never breaks.
"""
import logging
import math
import re
import time
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.config import settings
from app.models.knowledge import KnowledgeDocument

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────
TOP_K = 5                   # more candidates for semantic search (was 3)
CONTEXT_CHAR_BUDGET = 6000  # hard cap on the final context string sent to the LLM
PINECONE_BATCH_SIZE = 100   # free-tier friendly upsert batch size
MIN_SCORE_THRESHOLD = 0.25  # ignore chunks below this cosine similarity

_WORD_RE = re.compile(r"\w+")

# ──────────────────────────────────────────────────────────────────────
# Singletons (lazy-initialised)
# ──────────────────────────────────────────────────────────────────────
_embedding_model = None
_pinecone_index = None


def _get_embedding_model():
    """Lazy-load the sentence-transformers model (runs on CPU)."""
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading embedding model: %s", settings.EMBEDDING_MODEL)
            _embedding_model = SentenceTransformer(
                settings.EMBEDDING_MODEL,
                device="cpu",
            )
            logger.info("Embedding model loaded successfully")
        except Exception as exc:
            logger.error("Failed to load embedding model: %s", exc)
            raise
    return _embedding_model


def _get_pinecone_index():
    """Lazy-init Pinecone client + index.  Auto-creates the index if needed
    (serverless spec, free-tier compatible)."""
    global _pinecone_index
    if _pinecone_index is not None:
        return _pinecone_index

    if not settings.PINECONE_API_KEY:
        return None  # Pinecone not configured — caller should fall back to TF-IDF

    try:
        from pinecone import Pinecone, ServerlessSpec

        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        index_name = settings.PINECONE_INDEX_NAME

        # Auto-create if the index doesn't exist yet
        existing = [idx.name for idx in pc.list_indexes()]
        if index_name not in existing:
            logger.info("Creating Pinecone index '%s' (dimension=%d, metric=cosine)",
                        index_name, settings.EMBEDDING_DIMENSION)
            pc.create_index(
                name=index_name,
                dimension=settings.EMBEDDING_DIMENSION,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud=settings.PINECONE_CLOUD,
                    region=settings.PINECONE_REGION,
                ),
            )
            # Wait until the index is ready
            import time as _time
            while not pc.describe_index(index_name).status.get("ready", False):
                _time.sleep(1)
            logger.info("Pinecone index '%s' created and ready", index_name)

        _pinecone_index = pc.Index(index_name)
        logger.info("Connected to Pinecone index '%s'", index_name)
        return _pinecone_index

    except Exception as exc:
        logger.error("Pinecone init failed: %s", exc)
        return None


# ──────────────────────────────────────────────────────────────────────
# Embedding helper
# ──────────────────────────────────────────────────────────────────────

def _embed(texts: List[str]) -> List[List[float]]:
    """Embed a batch of text strings → list of float vectors."""
    model = _get_embedding_model()
    vectors = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return vectors.tolist()


# ──────────────────────────────────────────────────────────────────────
# Chunking (reuses the existing settings.CHUNK_SIZE / CHUNK_OVERLAP)
# ──────────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _chunk_offsets(length: int, size: int, overlap: int) -> List[Tuple[int, int]]:
    """Character offsets for chunks of `size` with `overlap` characters shared
    between consecutive chunks, covering the full [0, length) range."""
    if length <= 0:
        return []

    overlap = max(0, min(overlap, size - 1))
    step = size - overlap

    offsets = []
    i = 0
    while i < length:
        end = min(i + size, length)
        offsets.append((i, end))
        if end >= length:
            break
        i += step
    return offsets


def _make_chunks(doc_id: str, filename: str, content_text: str) -> List[dict]:
    """Split document text into chunks with metadata."""
    norm_text = _normalize(content_text)
    if not norm_text:
        return []

    offsets = _chunk_offsets(len(norm_text), settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
    chunks = []
    for idx, (start, end) in enumerate(offsets):
        chunk_text = norm_text[start:end]
        chunks.append({
            "id": f"{doc_id}#chunk{idx}",
            "text": chunk_text,
            "metadata": {
                "doc_id": doc_id,
                "filename": filename,
                "chunk_index": idx,
                "start": start,
                "end": end,
                "text": chunk_text,  # stored in metadata for retrieval
            },
        })
    return chunks


# ──────────────────────────────────────────────────────────────────────
# Document indexing  (called from crud/knowledge.py on upload)
# ──────────────────────────────────────────────────────────────────────

def index_document(doc_id: str, filename: str, content_text: str) -> int:
    """Chunk → embed → upsert to Pinecone.  Returns number of vectors upserted.
    Safe to call even when Pinecone is not configured (returns 0)."""
    index = _get_pinecone_index()
    if index is None:
        logger.warning("Pinecone not configured — skipping document indexing for %s", filename)
        return 0

    chunks = _make_chunks(doc_id, filename, content_text)
    if not chunks:
        return 0

    # Embed all chunk texts
    texts = [c["text"] for c in chunks]
    vectors = _embed(texts)

    # Upsert in batches (free-tier friendly)
    total = 0
    for batch_start in range(0, len(chunks), PINECONE_BATCH_SIZE):
        batch_end = batch_start + PINECONE_BATCH_SIZE
        batch = [
            (chunks[i]["id"], vectors[i], chunks[i]["metadata"])
            for i in range(batch_start, min(batch_end, len(chunks)))
        ]
        index.upsert(vectors=batch)
        total += len(batch)

    logger.info("Indexed %d chunks for document '%s' (id=%s)", total, filename, doc_id)
    return total


def delete_document_vectors(doc_id: str) -> bool:
    """Delete all vectors for a given document from Pinecone.
    Returns True on success, False if Pinecone is unavailable."""
    index = _get_pinecone_index()
    if index is None:
        return False

    try:
        # Pinecone serverless supports filter-based delete
        index.delete(filter={"doc_id": {"$eq": doc_id}})
        logger.info("Deleted vectors for doc_id=%s from Pinecone", doc_id)
        return True
    except Exception as exc:
        logger.error("Failed to delete vectors for doc_id=%s: %s", doc_id, exc)
        return False


# ──────────────────────────────────────────────────────────────────────
# Semantic retrieval  (the main public function — same interface)
# ──────────────────────────────────────────────────────────────────────

def retrieve_context(db: Session, query: str, top_k: int = TOP_K) -> str:
    """Returns the top-k most relevant chunks from Pinecone, concatenated
    into a single budgeted context string.

    Falls back to TF-IDF when Pinecone is not configured.

    The signature is preserved: `retrieve_context(db, query, top_k) -> str`
    so all existing call sites continue working without changes.
    """
    if not query or not query.strip():
        return ""

    index = _get_pinecone_index()
    if index is None:
        # Pinecone not available — use the legacy TF-IDF fallback
        return _tfidf_retrieve_context(db, query, top_k)

    try:
        return _pinecone_retrieve(query, top_k)
    except Exception as exc:
        logger.error("Pinecone retrieval failed, falling back to TF-IDF: %s", exc)
        return _tfidf_retrieve_context(db, query, top_k)


def _pinecone_retrieve(query: str, top_k: int) -> str:
    """Embed query → Pinecone similarity search → formatted context string."""
    # Embed the query
    query_vector = _embed([query])[0]

    # Query Pinecone
    index = _get_pinecone_index()
    results = index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True,
    )

    if not results.get("matches"):
        return ""

    # Filter by score threshold and assemble context
    parts = []
    used_chars = 0

    for match in results["matches"]:
        score = match.get("score", 0)
        if score < MIN_SCORE_THRESHOLD:
            continue

        metadata = match.get("metadata", {})
        filename = metadata.get("filename", "unknown")
        chunk_text = metadata.get("text", "")

        if not chunk_text:
            continue

        block = f"[Source: {filename}]\n{chunk_text}"

        if used_chars + len(block) > CONTEXT_CHAR_BUDGET:
            remaining = CONTEXT_CHAR_BUDGET - used_chars
            if remaining > len(f"[Source: {filename}]\n") + 20:
                parts.append(block[:remaining].rstrip() + "...")
            break

        parts.append(block)
        used_chars += len(block)

    return "\n\n".join(parts)


# ══════════════════════════════════════════════════════════════════════
# TF-IDF FALLBACK  (the original implementation, preserved verbatim)
# ══════════════════════════════════════════════════════════════════════

class _Chunk:
    __slots__ = ("doc_id", "filename", "start", "end", "text", "tokens")

    def __init__(self, doc_id: str, filename: str, start: int, end: int, text: str):
        self.doc_id = doc_id
        self.filename = filename
        self.start = start
        self.end = end
        self.text = text
        self.tokens = _WORD_RE.findall(text.lower())


def _tfidf_score(query_terms: List[str], chunk: "_Chunk", idf: dict) -> float:
    if not chunk.tokens:
        return 0.0

    tf = {}
    for tok in chunk.tokens:
        tf[tok] = tf.get(tok, 0) + 1

    raw_score = sum(
        tf.get(term, 0) * idf.get(term, 0.0)
        for term in query_terms
    )
    if raw_score <= 0:
        return 0.0

    return raw_score / math.sqrt(len(chunk.tokens))


def _diversity_cap(top_k: int) -> int:
    return max(1, (top_k // 2) + 1)


def _merge_selected(selected: List[Tuple["_Chunk", float]], doc_text_by_id: dict) -> List[Tuple[str, str, float]]:
    """Merge adjacent/overlapping chunks from the same document."""
    by_doc = {}
    for chunk, score in selected:
        by_doc.setdefault(chunk.doc_id, []).append((chunk, score))

    merged_blocks = []
    for doc_id, items in by_doc.items():
        items.sort(key=lambda pair: pair[0].start)
        doc_text = doc_text_by_id[doc_id]

        current_start, current_end = items[0][0].start, items[0][0].end
        current_best_score = items[0][1]
        current_filename = items[0][0].filename

        for chunk, score in items[1:]:
            if chunk.start <= current_end:
                current_end = max(current_end, chunk.end)
                current_best_score = max(current_best_score, score)
            else:
                merged_blocks.append(
                    (current_filename, doc_text[current_start:current_end], current_best_score)
                )
                current_start, current_end = chunk.start, chunk.end
                current_best_score = score

        merged_blocks.append(
            (current_filename, doc_text[current_start:current_end], current_best_score)
        )

    merged_blocks.sort(key=lambda block: block[2], reverse=True)
    return merged_blocks


def _tfidf_retrieve_context(db: Session, query: str, top_k: int = 3) -> str:
    """Legacy TF-IDF retrieval — used as fallback when Pinecone is unavailable."""
    query_terms = list(dict.fromkeys(_WORD_RE.findall(query.lower())))
    if not query_terms:
        return ""

    docs = (
        db.query(KnowledgeDocument)
        .filter(KnowledgeDocument.status == "ready")
        .all()
    )
    if not docs:
        return ""

    all_chunks: List[_Chunk] = []
    doc_text_by_id = {}

    for doc in docs:
        norm_text = _normalize(doc.content_text or "")
        if not norm_text:
            continue
        doc_text_by_id[doc.id] = norm_text

        offsets = _chunk_offsets(len(norm_text), settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
        for start, end in offsets:
            all_chunks.append(_Chunk(doc.id, doc.filename, start, end, norm_text[start:end]))

    if not all_chunks:
        return ""

    n_chunks = len(all_chunks)
    df = {term: 0 for term in query_terms}
    for chunk in all_chunks:
        chunk_term_set = set(chunk.tokens)
        for term in query_terms:
            if term in chunk_term_set:
                df[term] += 1

    idf = {
        term: math.log((1 + n_chunks) / (1 + df[term])) + 1.0
        for term in query_terms
    }

    scored = [
        (chunk, _tfidf_score(query_terms, chunk, idf))
        for chunk in all_chunks
    ]
    scored = [(c, s) for c, s in scored if s > 0]
    scored.sort(key=lambda pair: pair[1], reverse=True)

    if not scored:
        return ""

    cap = _diversity_cap(top_k)
    per_doc_count = {}
    selected: List[Tuple[_Chunk, float]] = []

    for chunk, score in scored:
        if len(selected) >= top_k:
            break
        if per_doc_count.get(chunk.doc_id, 0) >= cap:
            continue
        selected.append((chunk, score))
        per_doc_count[chunk.doc_id] = per_doc_count.get(chunk.doc_id, 0) + 1

    if not selected:
        return ""

    merged_blocks = _merge_selected(selected, doc_text_by_id)

    parts = []
    used_chars = 0
    for filename, text, _score_val in merged_blocks:
        block = f"[Source: {filename}]\n{text}"
        if used_chars + len(block) > CONTEXT_CHAR_BUDGET:
            remaining = CONTEXT_CHAR_BUDGET - used_chars
            if remaining > len(f"[Source: {filename}]\n") + 20:
                parts.append(block[:remaining].rstrip() + "...")
            break
        parts.append(block)
        used_chars += len(block)

    return "\n\n".join(parts)