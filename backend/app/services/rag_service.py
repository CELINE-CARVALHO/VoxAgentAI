"""
Retrieval used to ground the LLM's responses in the uploaded knowledge base.

This is still not a vector DB — it's a lightweight, dependency-free TF-IDF-style
ranker over chunked document text. Swap in pgvector/embeddings later without
changing the call site (`retrieve_context(db, query, top_k)` keeps the same
signature and return type: a single formatted string).

Phase 3 upgrade over the previous version:
- Chunking now honors settings.CHUNK_SIZE / settings.CHUNK_OVERLAP instead of a
  hardcoded size with no overlap, so relevant sentences that used to get cut in
  half at a chunk boundary are now covered by the overlap of the next chunk.
- Scoring is TF * IDF (computed across the chunk corpus for this query) instead
  of a raw term-overlap count, so common words across every document no longer
  outweigh the specific terms that actually distinguish a relevant chunk.
- Chunk-length normalization prevents large chunks from winning purely by
  containing more words.
- Cross-document diversity: no single document can fill every top-k slot, so a
  question that partially matches two different documents gets context from
  both instead of just whichever one happened to score highest.
- Context merging: adjacent/overlapping selected chunks from the same document
  are merged back into one coherent block (using their original character
  offsets) instead of being emitted as separate, possibly-overlapping fragments.
- A character budget caps the final context so the prompt sent to the LLM
  stays bounded regardless of how many documents are in the knowledge base.
"""
import math
import re
from typing import List, Tuple

from sqlalchemy.orm import Session

from app.config import settings
from app.models.knowledge import KnowledgeDocument

TOP_K = 3
CONTEXT_CHAR_BUDGET = 6000  # hard cap on the final context string sent to the LLM

_WORD_RE = re.compile(r"\w+")


class _Chunk:
    __slots__ = ("doc_id", "filename", "start", "end", "text", "tokens")

    def __init__(self, doc_id: str, filename: str, start: int, end: int, text: str):
        self.doc_id = doc_id
        self.filename = filename
        self.start = start
        self.end = end
        self.text = text
        self.tokens = _WORD_RE.findall(text.lower())


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


def _score(query_terms: List[str], chunk: "_Chunk", idf: dict) -> float:
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

    # Length normalization so a big chunk doesn't win purely by containing
    # more words than a smaller, more precisely on-topic chunk.
    return raw_score / math.sqrt(len(chunk.tokens))


def _diversity_cap(top_k: int) -> int:
    """Max chunks any single document may contribute to the final top-k,
    so one large/verbose document can't crowd out everything else."""
    return max(1, (top_k // 2) + 1)


def _merge_selected(selected: List[Tuple["_Chunk", float]], doc_text_by_id: dict) -> List[Tuple[str, str, float]]:
    """Merge adjacent/overlapping chunks from the same document (by original
    character offsets) into single contiguous blocks. Returns a list of
    (filename, merged_text, best_score) ordered by best_score descending."""
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
            if chunk.start <= current_end:  # overlapping or adjacent -> merge
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


def retrieve_context(db: Session, query: str, top_k: int = TOP_K) -> str:
    """Returns the top-k most relevant, merged, ranked chunks across all
    *ready* documents, concatenated into a single budgeted context string."""
    query_terms = list(dict.fromkeys(_WORD_RE.findall(query.lower())))  # dedup, keep order
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

    # Document frequency for each query term across this call's chunk corpus,
    # so terms that appear in nearly every chunk (generic words) get a low
    # idf weight and terms unique to a few chunks get a high one.
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
        (chunk, _score(query_terms, chunk, idf))
        for chunk in all_chunks
    ]
    scored = [(c, s) for c, s in scored if s > 0]
    scored.sort(key=lambda pair: pair[1], reverse=True)

    if not scored:
        return ""

    # Cross-document diversity: walk the ranked list, cap how many chunks any
    # one document can contribute, stop once top_k chunks are selected.
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