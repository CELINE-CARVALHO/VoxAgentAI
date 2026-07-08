"""Uploaded knowledge-base documents used to ground AI responses (simple RAG)."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Text, Integer
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)  # pdf | docx | txt | md
    size_bytes = Column(Integer, nullable=False, default=0)

    content_text = Column(Text, nullable=True)  # extracted plain text, used for retrieval
    status = Column(String(20), nullable=False, default="processing")  # processing | ready | failed

    uploaded_at = Column(DateTime, default=datetime.utcnow)