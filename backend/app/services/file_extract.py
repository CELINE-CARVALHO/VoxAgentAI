"""Extracts plain text from uploaded knowledge-base files (pdf/docx/txt/md)."""
import io

from pypdf import PdfReader
from docx import Document


def extract_text(filename: str, raw_bytes: bytes) -> str:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext == "pdf":
        reader = PdfReader(io.BytesIO(raw_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if ext == "docx":
        doc = Document(io.BytesIO(raw_bytes))
        return "\n".join(p.text for p in doc.paragraphs)

    if ext in ("txt", "md", "csv"):
        return raw_bytes.decode("utf-8", errors="ignore")

    raise ValueError(f"Unsupported file type: .{ext}")