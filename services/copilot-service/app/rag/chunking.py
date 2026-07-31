"""Document loading + chunking for the RAG knowledge base.

WHY chunking exists at all: embedding models have a limited context
window (BGE-small: 512 tokens) and, more importantly, retrieval
precision degrades badly if a whole multi-page document is embedded as
a single vector - the vector becomes an average of every topic in the
document, useless for finding the one paragraph that actually answers
a specific question.

WHY paragraph-based chunking, not fixed character-count chunking: the
naive approach (just cut every N characters) frequently slices a
sentence or even a word in half at the boundary, corrupting the meaning
of whatever ends up in that chunk. Splitting on paragraph boundaries
first respects the document's own natural idea boundaries, then
greedily merges consecutive paragraphs up to a token budget.

WHY overlap between chunks: if an important sentence happens to sit
right at a chunk boundary, splitting there means it's incomplete in
BOTH resulting chunks. A small overlap (chunk N's last ~50 tokens are
repeated as chunk N+1's first ~50 tokens) means that sentence survives
intact in at least one chunk.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

CHUNK_SIZE_TOKENS = 500
CHUNK_OVERLAP_TOKENS = 50
# Rough word-to-token ratio for English text - good enough for sizing
# chunks consistently; we don't need exact tokenizer precision here.
WORDS_PER_TOKEN = 0.75


@dataclass
class Chunk:
    text: str
    source: str  # filename, e.g. "lbnl_fdd_review.txt"
    chunk_index: int  # position within that document, for citing "chunk 3 of X"


def _load_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages)


def _load_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_document(path: Path) -> str:
    """Extract raw text from a source document, regardless of format."""
    if path.suffix.lower() == ".pdf":
        return _load_pdf_text(path)
    return _load_text_file(path)


# Keep only normal printable text: ASCII letters/digits/punctuation,
# common Latin-1 accented letters (for author names etc.), and
# whitespace. Anything else gets dropped.
#
# This replaced TWO earlier, failed attempts at the same problem -
# worth understanding why, since the reasoning matters more than the
# final regex: first, denylisting specific "math symbol" Unicode
# ranges (wrong - didn't cover every garbled range actually present).
# Second, ftfy.fix_text() to reverse MOJIBAKE (wrong diagnosis - ftfy
# fixes text that was decoded with the WRONG encoding, recovering the
# real original character; it made no difference here, which is itself
# evidence this isn't mojibake). What's actually happening: some LaTeX-
# generated, math-heavy PDFs don't embed a proper character mapping for
# math-italic glyphs, so pypdf extracts placeholder codepoints that
# never corresponded to real text in the first place - there is no
# "correct" character to recover, because the PDF itself never stored
# one. That's why a denylist (guessing which ranges are "bad") kept
# failing: an allowlist (keeping only what's known-good) doesn't
# require correctly guessing every way text can go wrong.
_ALLOWED_CHARS_RE = re.compile(r"[^\x00-\x7E\u00C0-\u00FF\s]")


def _clean_text(text: str) -> str:
    """Strip common PDF-extraction noise: unrecoverable glyph garbage
    from math-heavy PDFs, repeated page headers/footers, excessive
    whitespace."""
    text = _ALLOWED_CHARS_RE.sub("", text)
    # Collapse 3+ blank lines down to 2 (paragraph break)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse repeated spaces/tabs
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _split_into_paragraphs(text: str) -> list[str]:
    """Split on blank-line boundaries (the natural paragraph separator
    in extracted text), dropping empty results."""
    paragraphs = [p.strip() for p in text.split("\n\n")]
    return [p for p in paragraphs if p]


def _word_count(text: str) -> int:
    return len(text.split())


def _token_estimate(text: str) -> float:
    return _word_count(text) / WORDS_PER_TOKEN


def chunk_text(text: str, source: str) -> list[Chunk]:
    """Greedily merge consecutive paragraphs up to CHUNK_SIZE_TOKENS,
    carrying CHUNK_OVERLAP_TOKENS of trailing text into the next chunk."""
    text = _clean_text(text)
    paragraphs = _split_into_paragraphs(text)

    chunks: list[Chunk] = []
    current_paragraphs: list[str] = []
    current_tokens = 0.0

    def flush() -> None:
        if not current_paragraphs:
            return
        chunk_text_value = "\n\n".join(current_paragraphs)
        chunks.append(Chunk(text=chunk_text_value, source=source, chunk_index=len(chunks)))

    for paragraph in paragraphs:
        paragraph_tokens = _token_estimate(paragraph)

        if current_tokens + paragraph_tokens > CHUNK_SIZE_TOKENS and current_paragraphs:
            flush()
            # Carry the last paragraph forward as overlap, if it's not
            # itself already bigger than the overlap budget.
            overlap_paragraph = current_paragraphs[-1]
            if _token_estimate(overlap_paragraph) <= CHUNK_OVERLAP_TOKENS:
                current_paragraphs = [overlap_paragraph]
                current_tokens = _token_estimate(overlap_paragraph)
            else:
                current_paragraphs = []
                current_tokens = 0.0

        current_paragraphs.append(paragraph)
        current_tokens += paragraph_tokens

    flush()
    return chunks


def load_and_chunk_all(source_dir: Path) -> list[Chunk]:
    """Load every document in source_dir and chunk it, returning one
    flat list across all documents (each chunk keeps its own source
    filename for attribution)."""
    all_chunks: list[Chunk] = []
    for path in sorted(source_dir.iterdir()):
        if path.suffix.lower() not in (".pdf", ".txt"):
            continue
        raw_text = load_document(path)
        all_chunks.extend(chunk_text(raw_text, source=path.name))
    return all_chunks
