"""ChromaDB-backed vector storage and retrieval.

A "collection" in ChromaDB is roughly a table: a named group of
vectors, each with an ID, its embedding, the original text ("document"
in Chroma's terminology), and metadata. This project uses one
collection - hvac_fault_docs - for the whole knowledge base.

Chroma runs EMBEDDED here (a Python library writing to a local folder,
via PersistentClient), not as a separate server process - the simplest
option for this project's scale, and why no extra service/container is
needed for it in docker-compose.
"""

from typing import Any, cast

import chromadb

from app.config import settings
from app.rag.chunking import Chunk
from app.rag.embeddings import embed_documents, embed_query

COLLECTION_NAME = "hvac_fault_docs"

_client: chromadb.ClientAPI | None = None


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return _client


def _get_collection() -> chromadb.Collection:
    client = _get_client()
    return client.get_or_create_collection(COLLECTION_NAME)


def index_chunks(chunks: list[Chunk]) -> int:
    """Embed and store a batch of chunks. Returns the number stored.

    IDs are deterministic (source + chunk_index), not random UUIDs - so
    re-running this on the same documents overwrites the same entries
    instead of duplicating them. Matters for a knowledge base that gets
    rebuilt as documents are added/changed, not just written once.
    """
    if not chunks:
        return 0

    ids = [f"{c.source}::{c.chunk_index}" for c in chunks]
    texts = [c.text for c in chunks]
    metadatas: list[dict[str, str | int]] = [
        {"source": c.source, "chunk_index": c.chunk_index} for c in chunks
    ]
    embeddings = embed_documents(texts)

    collection = _get_collection()
    # chromadb's own stubs expect numpy arrays or narrower Sequence
    # types than plain list[list[float]] - the runtime accepts this
    # shape fine (confirmed live, not just assumed), the cast just
    # tells mypy what we already know to be true from testing.
    collection.upsert(
        ids=ids,
        embeddings=cast(Any, embeddings),
        documents=texts,
        metadatas=cast(Any, metadatas),
    )
    return len(chunks)


def retrieve(query: str, n_results: int = 4) -> list[dict]:
    """Embed a query and return the n_results most similar chunks, each
    with its text, source, and a similarity distance (lower = closer)."""
    collection = _get_collection()
    query_embedding = embed_query(query)

    results = collection.query(query_embeddings=cast(Any, [query_embedding]), n_results=n_results)

    # chromadb's return type marks these Optional (a query COULD return
    # no results structure at all in principle), but a successful query
    # call always populates them - asserting here documents that
    # assumption explicitly rather than silencing it.
    documents = results["documents"]
    metadatas = results["metadatas"]
    distances = results["distances"]
    assert documents is not None and metadatas is not None and distances is not None

    retrieved = []
    for text, metadata, distance in zip(documents[0], metadatas[0], distances[0], strict=False):
        retrieved.append(
            {
                "text": text,
                "source": metadata["source"],
                "chunk_index": metadata["chunk_index"],
                "distance": distance,
            }
        )
    return retrieved
