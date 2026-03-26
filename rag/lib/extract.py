"""
Text extraction from PDF and plain text files.

Returns extracted text plus page boundary metadata for PDFs.
"""

import os
from dataclasses import dataclass


@dataclass
class ExtractedDoc:
    text: str
    pages: list[tuple[int, int]] | None  # [(page_num, char_offset), ...] or None for plain text
    source: str                           # original file path
    page_count: int


def extract_pdf(path: str) -> ExtractedDoc:
    """Extract text from a PDF file with page boundary tracking."""
    import pymupdf

    doc = pymupdf.open(path)
    text_parts = []
    pages = []
    offset = 0

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_text = page.get_text("text")
        if page_text.strip():
            pages.append((page_num + 1, offset))  # 1-indexed page numbers
            text_parts.append(page_text)
            offset += len(page_text)

    doc.close()
    full_text = "".join(text_parts)

    return ExtractedDoc(
        text=full_text,
        pages=pages,
        source=os.path.abspath(path),
        page_count=len(pages),
    )


def extract_text(path: str) -> ExtractedDoc:
    """Extract text from a plain text file."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    return ExtractedDoc(
        text=text,
        pages=None,
        source=os.path.abspath(path),
        page_count=1,
    )


def extract(path: str) -> ExtractedDoc:
    """Auto-detect file type and extract text."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return extract_pdf(path)
    elif ext in (".txt", ".md", ".csv", ".json", ".log", ".rst", ".html", ".htm"):
        return extract_text(path)
    else:
        # Try as plain text
        return extract_text(path)
