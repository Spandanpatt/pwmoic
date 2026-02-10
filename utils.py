"""File and text utilities for pitch deck ingestion."""

import io
import re
from typing import Optional

# Lazy imports inside extract_text_from_file to fail gracefully per file type


def extract_text_from_file(uploaded_file) -> str:
    """
    Extract all text from an uploaded file (PDF, PPTX, DOCX, or TXT).
    Returns extracted text or empty string on unsupported/error. Handles errors gracefully.
    """
    if uploaded_file is None:
        return ""

    name = (getattr(uploaded_file, "name", None) or "").lower()
    raw = getattr(uploaded_file, "read", None)
    if not callable(raw):
        return ""

    try:
        raw.seek(0)
    except Exception:
        pass

    data = b""
    try:
        data = raw()
        if isinstance(data, str):
            return data.strip() if data else ""
    except Exception:
        return ""

    if not data:
        return ""

    # TXT
    if name.endswith(".txt"):
        try:
            return data.decode("utf-8", errors="replace").strip()
        except Exception:
            return data.decode("latin-1", errors="replace").strip()

    # PDF
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            parts = []
            for page in reader.pages:
                try:
                    parts.append(page.extract_text() or "")
                except Exception:
                    parts.append("")
            return "\n\n".join(parts).strip()
        except ImportError:
            return ""
        except Exception:
            return ""

    # PPTX
    if name.endswith(".pptx"):
        try:
            from pptx import Presentation
            prs = Presentation(io.BytesIO(data))
            parts = []
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text:
                        parts.append(shape.text.strip())
            return "\n\n".join(parts).strip()
        except ImportError:
            return ""
        except Exception:
            return ""

    # DOCX
    if name.endswith(".docx"):
        try:
            import docx2txt
            text = docx2txt.process(io.BytesIO(data))
            return (text or "").strip()
        except ImportError:
            return ""
        except Exception:
            return ""

    return ""


def extract_document_date(text: str) -> Optional[str]:
    """
    Try to extract a document/pitch date from text (e.g. "January 2024", "Q3 2023", "2023").
    Returns ISO-style date string or None if not found.
    """
    if not (text or "").strip():
        return None
    # Common patterns: "January 2024", "Jan 2024", "2024", "Q1 2024", "Fall 2023"
    patterns = [
        r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})",
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+(\d{4})",
        r"Q[1-4]\s+(\d{4})",
        r"(?:Fall|Spring|Summer|Winter)\s+(\d{4})",
        r"\b(20\d{2})\b",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None
