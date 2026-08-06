from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json

MIN_DOCUMENTS = 4


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """TODO(student): tao bo evaluation set tu cleaned dataframe.

    Pseudo-code:
    1. Kiem tra so luong document toi thieu.
    2. Chon mot so paper dai dien.
    3. Tao nhieu loai cau hoi:
       - summary
       - authors
       - date
       - categories
    4. Moi row can co:
       - id
       - question_type
       - question
       - ground_truth
       - ground_truth_doc_ids
    5. Ghi file JSON vao output_path.
    """
    if len(df) < MIN_DOCUMENTS:
        raise ValueError(f"Need at least {MIN_DOCUMENTS} cleaned documents to build a test set.")

    sample = df.head(min(8, len(df))).reset_index(drop=True)
    test_set: list[dict[str, Any]] = []
    counter = 1

    for _, row in sample.iterrows():
        paper_id = str(row["paper_id"])
        title = str(row["title"])
        summary = str(row["summary"])
        authors = str(row.get("authors_joined") or "")
        published = str(row.get("published") or "")
        categories = str(row.get("categories_joined") or row.get("primary_category") or "unknown")

        candidates = [
            {
                "question_type": "summary",
                "question": f"What is the paper '{title}' about?",
                "ground_truth": first_sentence(summary),
            },
            {
                "question_type": "authors",
                "question": f"Who are the authors of the paper '{title}'?",
                "ground_truth": authors or "Unknown authors",
            },
            {
                "question_type": "date",
                "question": f"When was the paper '{title}' published?",
                "ground_truth": published or "Unknown date",
            },
            {
                "question_type": "categories",
                "question": f"What categories or subjects are associated with '{title}'?",
                "ground_truth": categories,
            },
        ]

        for item in candidates:
            if not item["ground_truth"] or item["ground_truth"].lower().startswith("unknown"):
                continue
            test_set.append(
                {
                    "id": f"q{counter:03d}",
                    "question_type": item["question_type"],
                    "question": item["question"],
                    "ground_truth": item["ground_truth"],
                    "ground_truth_doc_ids": [paper_id],
                }
            )
            counter += 1

    if len(test_set) < MIN_DOCUMENTS:
        raise ValueError("Failed to create a sufficiently diverse evaluation set.")

    write_json(Path(output_path), test_set)
    return test_set
