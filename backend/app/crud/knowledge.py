from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeDocument
from app.services.file_extract import extract_text


def create_document(db: Session, filename: str, raw_bytes: bytes) -> KnowledgeDocument:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else "txt"

    doc = KnowledgeDocument(
        filename=filename,
        file_type=ext,
        size_bytes=len(raw_bytes),
        status="processing",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    try:
        text = extract_text(filename, raw_bytes)
        doc.content_text = text
        doc.status = "ready"
    except Exception:
        doc.status = "failed"

    db.commit()
    db.refresh(doc)
    return doc