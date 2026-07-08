import uuid
from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict


class KnowledgeDocOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    file_type: str
    size_bytes: int
    status: str
    uploaded_at: datetime


class KnowledgeListOut(BaseModel):
    items: List[KnowledgeDocOut]
    total: int