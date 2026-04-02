"""
One-time script to ingest all past proposals into the vector database.
Run this once after copying proposals into the proposals folder.
Run again whenever you add new proposals.

Usage:
    python ingest/run_ingestion.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PROPOSALS_FOLDER
from ingest.proposal_processor import load_all_proposals
from ingest.vector_store import index_proposals, get_index_stats


def main():
    print("=" * 60)
    print("PROPOSAL ENGINE — Ingestion Pipeline")
    print("=" * 60)
    print(f"\nReading proposals from: {PROPOSALS_FOLDER}\n")

    proposals = load_all_proposals(PROPOSALS_FOLDER)

    if not proposals:
        print("\nNo proposals found. Check the folder path in your .env file.")
        return

    print(f"\nIndexing {len(proposals)} proposals into vector database...\n")
    added = index_proposals(proposals)

    stats = get_index_stats()
    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    print(f"  Proposals indexed this run : {added}")
    print(f"  Total proposals in database: {stats['unique_proposals']}")
    print(f"  Total chunks stored        : {stats['total_chunks']}")
    print("\nProposals in database:")
    for name in stats["filenames"]:
        print(f"  - {name}")
    print("\nReady. You can now run the proposal engine.")


if __name__ == "__main__":
    main()
