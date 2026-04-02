"""
Manages the ChromaDB vector database.
Stores past proposals as searchable knowledge.
When a new RFP comes in, retrieves the most relevant past proposals as context.
"""
import chromadb
from chromadb.utils import embedding_functions
from config import VECTOR_DB_PATH

COLLECTION_NAME = "past_proposals"


def get_collection():
    """Connect to (or create) the local ChromaDB collection."""
    client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
    ef = embedding_functions.DefaultEmbeddingFunction()
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def index_proposals(proposals: list[dict]) -> int:
    """
    Add proposals to the vector database.
    proposals: list of {filename, text, file_path}
    Returns count of newly added proposals.
    """
    collection = get_collection()

    # Get already-indexed filenames to avoid duplicates
    existing = set()
    if collection.count() > 0:
        existing_data = collection.get()
        existing = set(existing_data.get("ids", []))

    added = 0
    for proposal in proposals:
        doc_id = proposal["filename"]
        if doc_id in existing:
            print(f"  Already indexed: {proposal['filename']}")
            continue

        # Split into chunks of ~1000 words to stay within embedding limits
        chunks = chunk_text(proposal["text"], max_words=1000)
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}__chunk{i}"
            if chunk_id not in existing:
                collection.add(
                    ids=[chunk_id],
                    documents=[chunk],
                    metadatas=[{
                        "filename": proposal["filename"],
                        "file_path": proposal["file_path"],
                        "chunk_index": i,
                    }]
                )
        added += 1
        print(f"  Indexed: {proposal['filename']} ({len(chunks)} chunks)")

    return added


def search_similar_proposals(query: str, n_results: int = 5) -> list[dict]:
    """
    Find the most relevant past proposals for a given RFP query.
    Returns list of {filename, text_chunk, relevance_score}
    """
    collection = get_collection()
    if collection.count() == 0:
        return []

    results = collection.query(
        query_texts=[query],
        n_results=min(n_results * 3, collection.count()),  # over-fetch then dedupe
    )

    # Deduplicate by filename, keep highest-scoring chunk per proposal
    seen_files = {}
    for doc, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        filename = meta["filename"]
        score = 1 - distance  # convert distance to similarity score
        if filename not in seen_files or score > seen_files[filename]["score"]:
            seen_files[filename] = {
                "filename": filename,
                "text_chunk": doc,
                "score": round(score, 3),
            }

    # Return top n_results sorted by score
    ranked = sorted(seen_files.values(), key=lambda x: x["score"], reverse=True)
    return ranked[:n_results]


def get_index_stats() -> dict:
    """Return stats about what's in the vector database."""
    collection = get_collection()
    count = collection.count()
    if count == 0:
        return {"total_chunks": 0, "unique_proposals": 0, "filenames": []}

    data = collection.get()
    filenames = list({m["filename"] for m in data["metadatas"]})
    return {
        "total_chunks": count,
        "unique_proposals": len(filenames),
        "filenames": sorted(filenames),
    }


def chunk_text(text: str, max_words: int = 1000) -> list[str]:
    """Split text into chunks of max_words."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i:i + max_words])
        chunks.append(chunk)
    return chunks
