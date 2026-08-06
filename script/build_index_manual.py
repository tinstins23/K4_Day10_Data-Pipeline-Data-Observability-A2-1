"""Manual/temporary script to build the ChromaDB index directly from data/clean/papers_clean.json.

Dung tam trong luc cho `src/pipelines/phase1.py` duoc ghep xong boi Thanh vien 3.
Khong phai mot phan cua pipeline chinh thuc (khong duoc goi trong script/run_phase1.py).

Chay:
    uv run python script/build_index_manual.py
"""

from __future__ import annotations

import pandas as pd

from core.config import load_settings
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    settings = load_settings()
    df = pd.read_json(settings.paths.clean_json)
    print(f"Loaded {len(df)} cleaned records from {settings.paths.clean_json}")

    index = LocalEmbeddingIndex.build(df, settings)
    print(f"Index built. Collection: {index.collection_name}")
    print(f"Manifest written to: {settings.paths.embeddings_json}")
    print(f"Chroma persisted to: {settings.paths.chroma_dir}")

    # Quick sanity check: search + exact lookup
    sample_title = df.iloc[0]["title"]
    print(f"\nSample search for: {sample_title!r}")
    for result in index.search(sample_title, top_k=3):
        print(f"  score={result.score:.4f} paper_id={result.paper_id} title={result.title[:70]}")

    sample_paper_id = df.iloc[0]["paper_id"]
    exact = index.lookup(sample_paper_id)
    print(f"\nExact lookup by paper_id={sample_paper_id!r}: {'OK' if exact else 'NOT FOUND'}")


if __name__ == "__main__":
    main()
