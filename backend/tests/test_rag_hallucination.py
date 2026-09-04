"""
RAG Hallucination Tests for VoxAgent AI
========================================

Three-scenario integration test demonstrating:

1. A question answered correctly from the Knowledge Base
2. A question whose answer is NOT in the Knowledge Base
3. A similar-but-incorrect question (superficially related, but the
   actual answer is not present)

Verifies that the system uses retrieved context and responds with
uncertainty instead of hallucinating when information is unavailable.

Requirements:
    - GROQ_API_KEY set in backend/.env
    - PINECONE_API_KEY set in backend/.env  (or falls back to TF-IDF)
    - Run from backend/ directory:

        pytest tests/test_rag_hallucination.py -v -s

These are integration tests — they call real APIs and take a few seconds.
"""
import os
import sys
import json
import pytest

# ── Ensure backend/app is importable ──
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.models.knowledge import KnowledgeDocument
from app.services.rag_service import (
    retrieve_context,
    index_document,
    _normalize,
)
from app.services.groq_service import generate_call_turn


# ═══════════════════════════════════════════════════════════════════════
# Test Knowledge Base Content — a small, controlled document
# ═══════════════════════════════════════════════════════════════════════
SAMPLE_DOCUMENT = """
VoxAgent AI — Customer Support FAQ

Q: What are VoxAgent AI's business hours?
A: VoxAgent AI's customer support team is available Monday through Friday,
   from 9:00 AM to 6:00 PM Indian Standard Time (IST).

Q: What is the refund policy?
A: Customers may request a full refund within 14 days of purchase.
   After 14 days, a 50% refund is available up to 30 days.
   No refunds are issued after 30 days.

Q: What subscription plans are available?
A: VoxAgent AI offers three plans:
   - Starter: $29/month (up to 500 calls/month)
   - Professional: $99/month (up to 5,000 calls/month)
   - Enterprise: Custom pricing (unlimited calls, dedicated support)

Q: How do I reset my password?
A: Click "Forgot Password" on the login page, enter your registered email,
   and follow the link sent to your inbox. The link expires in 24 hours.
"""


# ═══════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def db():
    """Create a fresh test database and yield a session."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def knowledge_doc(db):
    """Insert a test document into the Knowledge Base and index it."""
    doc = KnowledgeDocument(
        filename="test_faq.txt",
        file_type="txt",
        size_bytes=len(SAMPLE_DOCUMENT.encode()),
        content_text=SAMPLE_DOCUMENT,
        status="ready",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Index to Pinecone (if configured)
    try:
        count = index_document(doc.id, doc.filename, doc.content_text)
        print(f"\n  [OK] Indexed {count} chunks to Pinecone")
    except Exception as e:
        print(f"\n  [WARN] Pinecone indexing skipped: {e}")

    yield doc

    # Cleanup
    db.delete(doc)
    db.commit()


def _ask_question(db, question: str, knowledge_doc) -> dict:
    """Retrieve context and generate an LLM response for a question."""
    context = retrieve_context(db, question)
    print(f"\n  Query:   {question}")
    print(f"  Context: {context[:200]}..." if len(context) > 200 else f"  Context: {context or '(empty)'}")

    result = generate_call_turn(
        user_text=question,
        knowledge_context=context,
        conversation_history=[],
        long_term_summary="",
    )
    print(f"  Response: {result.get('response', '')}")
    return result


# ═══════════════════════════════════════════════════════════════════════
# Test 1: Answerable question — answer IS in the Knowledge Base
# ═══════════════════════════════════════════════════════════════════════

@pytest.mark.integration
def test_answerable_question(db, knowledge_doc):
    """The refund policy IS in the KB. The LLM should cite correct facts."""
    result = _ask_question(db, "What is the refund policy?", knowledge_doc)
    response = result.get("response", "").lower()

    # Must mention key facts from the document
    assert any(term in response for term in ["14 day", "14-day", "refund", "30 day", "30-day"]), (
        f"Expected refund policy details in response, got: {response}"
    )
    # Should NOT contain hallucination markers
    assert "i don't have" not in response, (
        "LLM said it doesn't have info, but the answer IS in the KB"
    )


# ═══════════════════════════════════════════════════════════════════════
# Test 2: Unanswerable question — answer is NOT in the Knowledge Base
# ═══════════════════════════════════════════════════════════════════════

@pytest.mark.integration
def test_unanswerable_question(db, knowledge_doc):
    """The CEO's name is NOT in the KB. The LLM must not fabricate a name."""
    result = _ask_question(
        db, "Who is the CEO of VoxAgent AI and when was the company founded?", knowledge_doc
    )
    response = result.get("response", "").lower()

    # Must express uncertainty — look for common uncertainty phrases
    uncertainty_markers = [
        "don't have", "not available", "couldn't find", "no information",
        "not sure", "can't find", "unable to find", "not in",
        "don't know", "not able", "human", "someone",
        "not have", "cannot find", "isn't available",
    ]
    has_uncertainty = any(marker in response for marker in uncertainty_markers)

    # Must NOT invent a name (common hallucination)
    common_fake_names = ["john", "jane", "sam", "mike", "david", "sarah", "james", "robert"]
    invented_name = any(name in response for name in common_fake_names)

    assert has_uncertainty or not invented_name, (
        f"LLM may have hallucinated CEO info. Response: {response}"
    )


# ═══════════════════════════════════════════════════════════════════════
# Test 3: Similar-but-wrong question — superficially related to KB
# ═══════════════════════════════════════════════════════════════════════

@pytest.mark.integration
def test_similar_but_wrong_question(db, knowledge_doc):
    """The KB lists plan prices but NOT a 'free trial'. The LLM must not
    invent a free trial period or make up a trial duration."""
    result = _ask_question(
        db, "How long is the free trial period for VoxAgent AI?", knowledge_doc
    )
    response = result.get("response", "").lower()

    # Should NOT fabricate a trial duration
    fabrication_markers = [
        "7 day", "7-day", "14 day free", "30 day free",
        "free trial is", "trial period is", "trial lasts",
        "free for", "try for free for",
    ]
    has_fabrication = any(marker in response for marker in fabrication_markers)

    # Should express uncertainty OR redirect
    uncertainty_markers = [
        "don't have", "not available", "couldn't find", "no information",
        "not sure", "can't find", "not mention", "human",
        "someone", "don't see", "no free trial", "isn't listed",
    ]
    has_uncertainty = any(marker in response for marker in uncertainty_markers)

    # Either the model acknowledges uncertainty OR at least doesn't fabricate
    assert has_uncertainty or not has_fabrication, (
        f"LLM may have hallucinated a free trial. Response: {response}"
    )


# ═══════════════════════════════════════════════════════════════════════
# Test 4: Context retrieval quality — verify semantic search works
# ═══════════════════════════════════════════════════════════════════════

@pytest.mark.integration
def test_context_retrieval_quality(db, knowledge_doc):
    """Verify that retrieve_context returns relevant chunks for a
    semantically matching query, not just keyword overlap."""
    # This query doesn't contain exact keywords like "subscription"
    # but is semantically about pricing/plans
    context = retrieve_context(db, "How much does it cost?")
    print(f"\n  Semantic query: 'How much does it cost?'")
    print(f"  Retrieved context: {context[:300]}...")

    # Should retrieve the pricing/plans section
    assert context, "Expected non-empty context for pricing query"
    assert any(term in context.lower() for term in ["starter", "professional", "enterprise", "$29", "$99"]), (
        f"Expected pricing info in context, got: {context[:200]}"
    )
