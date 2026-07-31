"""Run once (or whenever source_docs/ changes) to (re)build the vector
index. Not wired into the FastAPI app's request path - indexing is a
deliberate, occasional maintenance action, not something that should
happen on every request or every service restart."""

from pathlib import Path

from app.rag.chunking import load_and_chunk_all
from app.rag.vector_store import index_chunks

SOURCE_DOCS_DIR = Path(__file__).parent.parent.parent / "data" / "source_docs"


def main() -> None:
    print(f"Loading and chunking documents from {SOURCE_DOCS_DIR}...")
    chunks = load_and_chunk_all(SOURCE_DOCS_DIR)
    print(f"Produced {len(chunks)} chunks.")

    print("Embedding and storing in ChromaDB...")
    count = index_chunks(chunks)
    print(f"Indexed {count} chunks.")


if __name__ == "__main__":
    main()
