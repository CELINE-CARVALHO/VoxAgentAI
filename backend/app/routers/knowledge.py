"""Knowledge Base page: upload docs, list/search/filter, delete, view content."""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.knowledge import KnowledgeDocument
from app.schemas.knowledge import KnowledgeDocOut, KnowledgeListOut
from app.crud.knowledge import create_document

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md", "csv"}
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


@router.post("/upload", response_model=KnowledgeDocOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ext = file.filename.lower().rsplit(".", 1)[-1] if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type .{ext}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    raw_bytes = await file.read()
    if len(raw_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds 20MB limit")

    doc = create_document(db, file.filename, raw_bytes)
    return doc


@router.get("", response_model=KnowledgeListOut)
def list_documents(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    search: Optional[str] = None,
    file_type: Optional[str] = None,
    status: Optional[str] = None,
):
    q = db.query(KnowledgeDocument)
    if search:
        q = q.filter(or_(KnowledgeDocument.filename.ilike(f"%{search}%")))
    if file_type:
        q = q.filter(KnowledgeDocument.file_type == file_type)
    if status:
        q = q.filter(KnowledgeDocument.status == status)

    items = q.order_by(KnowledgeDocument.uploaded_at.desc()).all()
    return KnowledgeListOut(items=items, total=len(items))


@router.get("/{doc_id}", response_model=KnowledgeDocOut)
def get_document(doc_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{doc_id}", status_code=204)
def delete_document(doc_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Clean up Pinecone vectors (best-effort)
    try:
        from app.services.rag_service import delete_document_vectors
        delete_document_vectors(str(doc_id))
    except Exception as exc:
        logger.warning("Failed to delete Pinecone vectors for doc %s: %s", doc_id, exc)

    db.delete(doc)
    db.commit()


@router.post("/reindex", status_code=200)
def reindex_all_documents(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Re-index all ready documents into Pinecone.

    Useful for bootstrapping when switching from TF-IDF to Pinecone,
    or after recreating the Pinecone index.
    """
    from app.services.rag_service import index_document

    docs = (
        db.query(KnowledgeDocument)
        .filter(KnowledgeDocument.status == "ready")
        .all()
    )

    results = {"total_docs": len(docs), "indexed": 0, "chunks": 0, "errors": []}

    for doc in docs:
        if not doc.content_text:
            continue
        try:
            count = index_document(doc.id, doc.filename, doc.content_text)
            results["indexed"] += 1
            results["chunks"] += count
        except Exception as exc:
            results["errors"].append({"doc_id": doc.id, "filename": doc.filename, "error": str(exc)})
            logger.error("Reindex failed for doc %s: %s", doc.id, exc)

    return results