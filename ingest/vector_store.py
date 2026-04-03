"""
Lightweight vector store using scikit-learn TF-IDF.
Replaces chromadb — no grpc/protobuf dependencies.
Stores index as a pickle file committed to the repo.
"""
import os
import pickle
from pathlib import Path

INDEX_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "proposal_index.pkl")


def index_proposals(proposals: list[dict]) -> int:
    """
    Build TF-IDF index from proposals and save to disk.
    proposals: list of {filename, text, file_path}
    Returns count of newly added proposals.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer

    existing = _load_index()
    existing_files = {p["filename"] for p in existing["proposals"]}

    added = 0
    for proposal in proposals:
        if proposal["filename"] in existing_files:
            print(f"  Already indexed: {proposal['filename']}")
            continue
        existing["proposals"].append({
            "filename": proposal["filename"],
            "text": proposal["text"],
        })
        added += 1
        print(f"  Indexed: {proposal['filename']}")

    if added > 0:
        # Rebuild TF-IDF matrix over all proposals
        texts = [p["text"] for p in existing["proposals"]]
        vectorizer = TfidfVectorizer(max_features=5000, stop_words="english", max_df=0.85)
        matrix = vectorizer.fit_transform(texts)
        existing["vectorizer"] = vectorizer
        existing["matrix"] = matrix
        _save_index(existing)

    return added


def search_similar_proposals(query: str, n_results: int = 5) -> list[dict]:
    """
    Find the most relevant past proposals for a given query.
    Returns list of {filename, text_chunk, score}
    """
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np

    index = _load_index()
    if not index["proposals"] or index.get("vectorizer") is None:
        return []

    vectorizer = index["vectorizer"]
    matrix = index["matrix"]

    query_vec = vectorizer.transform([query])
    scores = cosine_similarity(query_vec, matrix).flatten()
    top_indices = np.argsort(scores)[::-1][:n_results]

    results = []
    for i in top_indices:
        if scores[i] > 0:
            text = index["proposals"][i]["text"]
            results.append({
                "filename": index["proposals"][i]["filename"],
                "text_chunk": text[:1500],
                "score": round(float(scores[i]), 3),
            })
    return results


def get_index_stats() -> dict:
    """Return stats about the index."""
    index = _load_index()
    proposals = index.get("proposals", [])
    return {
        "total_chunks": len(proposals),
        "unique_proposals": len(proposals),
        "filenames": sorted([p["filename"] for p in proposals]),
    }


def _load_index() -> dict:
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, "rb") as f:
            return pickle.load(f)
    return {"proposals": [], "vectorizer": None, "matrix": None}


def _save_index(index: dict):
    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
    with open(INDEX_PATH, "wb") as f:
        pickle.dump(index, f)
