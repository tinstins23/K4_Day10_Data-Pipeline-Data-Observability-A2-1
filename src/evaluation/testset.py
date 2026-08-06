from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a deterministic, factual evaluation set from cleaned papers.

    Every question is grounded in a single cleaned row, which makes the
    expected document identifier unambiguous and lets the same set be reused
    for baseline, corrupted, and repaired collections.
    """
    required = {"paper_id", "title", "summary", "authors_joined", "published", "categories_joined"}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError("Clean dataframe is missing required columns: " + ", ".join(missing))

    candidates = df.copy()
    for column in required:
        candidates[column] = candidates[column].fillna("").astype(str).map(normalize_whitespace)
    candidates = candidates[
        candidates["paper_id"].ne("")
        & candidates["title"].ne("")
        & candidates["summary"].ne("")
    ].drop_duplicates(subset="paper_id").sort_values("paper_id")
    if candidates.empty:
        raise ValueError("Need at least one valid cleaned paper to build an evaluation set.")

    question_builders = (
        ("summary", lambda row: (f"What does the paper '{row.title}' study?", first_sentence(row.summary))),
        ("authors", lambda row: (f"Who authored the paper '{row.title}'?", row.authors_joined or "No authors listed.")),
        ("date", lambda row: (f"When was the paper '{row.title}' published?", row.published)),
        ("categories", lambda row: (f"What subject categories are listed for '{row.title}'?", row.categories_joined or "No categories listed.")),
    )
    selected = candidates.head(min(5, len(candidates)))
    test_set: list[dict[str, Any]] = []
    for row in selected.itertuples(index=False):
        for question_type, builder in question_builders:
            question, ground_truth = builder(row)
            test_set.append(
                {
                    "id": f"{question_type}-{row.paper_id}",
                    "question_type": question_type,
                    "question": question,
                    "ground_truth": ground_truth,
                    "ground_truth_doc_ids": [row.paper_id],
                }
            )

    write_json(output_path, test_set)
    return test_set
