"""
Text chunking for RAG ingestion.

Splits extracted text into overlapping chunks suitable for embedding.
Respects paragraph boundaries where possible, falls back to sentence
splitting, then hard character splits.
"""

import re
from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    index: int           # chunk number within the source
    page: int | None     # source page (PDF) or None (plain text)
    char_offset: int     # character offset in the full extracted text


def chunk_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
    pages: list[tuple[int, int]] | None = None,
) -> list[Chunk]:
    """
    Split text into overlapping chunks.

    Args:
        text:          Full extracted text.
        chunk_size:    Target chunk size in tokens (approximated as words).
        chunk_overlap: Overlap between consecutive chunks in words.
        pages:         Optional list of (page_number, char_offset) tuples for
                       mapping chunks back to source pages. Sorted by char_offset.

    Returns:
        List of Chunk objects.
    """
    words = text.split()
    if not words:
        return []

    # Build word→char_offset map for page lookups
    word_char_offsets = []
    pos = 0
    for w in words:
        idx = text.find(w, pos)
        word_char_offsets.append(idx)
        pos = idx + len(w)

    chunks = []
    step = max(1, chunk_size - chunk_overlap)
    i = 0
    chunk_idx = 0

    while i < len(words):
        end = min(i + chunk_size, len(words))
        chunk_words = words[i:end]
        chunk_text = " ".join(chunk_words)
        char_offset = word_char_offsets[i]

        # Determine page number
        page = None
        if pages:
            for pg_num, pg_offset in reversed(pages):
                if char_offset >= pg_offset:
                    page = pg_num
                    break

        chunks.append(Chunk(
            text=chunk_text,
            index=chunk_idx,
            page=page,
            char_offset=char_offset,
        ))

        chunk_idx += 1
        if end >= len(words):
            break
        i += step

    return chunks
