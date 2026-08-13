"""Embedding generation using BGE-small.

BGE (BAAI General Embedding) models are trained on a query/document
ASYMMETRY: retrieval performance improves when short QUERIES are
prefixed with an instruction string before embedding, but DOCUMENTS
being stored/retrieved should always be embedded as raw text, with no
prefix, in every BGE version. Getting this backwards doesn't crash
anything - it silently produces a worse vector, which only shows up as
degraded retrieval quality, not an error. That's what makes it a common,
easy-to-miss bug.

For bge-small-en-v1.5 specifically (the version this project uses),
BAAI's own model card notes v1.5 improved retrieval quality even WITHOUT
the query instruction - it's now optional, with only a slight quality
drop if omitted. We still apply it, since it's free (no runtime cost)
and the officially recommended setting.
"""

from typing import cast

from sentence_transformers import SentenceTransformer

from app.config import settings

QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Lazy singleton - the model's weights (~130MB) load once per
    process, not on every call."""
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.embedding_model_name)
    return _model


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed chunk text for STORAGE. No instruction prefix."""
    model = _get_model()
    embeddings = model.encode(texts, normalize_embeddings=True)
    # sentence-transformers' encode() return type isn't specific enough for
    # mypy to carry through .tolist() here - a known, real incomplete-stub
    # limitation, not a bug.
    return cast(list[list[float]], embeddings.tolist())


def embed_query(text: str) -> list[float]:
    """Embed a user's question for RETRIEVAL. Instruction prefix
    applied, per BGE's query/document asymmetry (see module docstring)."""
    model = _get_model()
    embedding = model.encode(QUERY_INSTRUCTION + text, normalize_embeddings=True)
    return embedding.tolist()
