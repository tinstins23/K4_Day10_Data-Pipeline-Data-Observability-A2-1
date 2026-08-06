from __future__ import annotations

from core.config import load_settings, require_llm_credentials
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """TODO(student): xay dung baseline pipeline end-to-end.

    Pseudo-code:
    1. Load settings.
    2. Load hoac fetch raw records.
    3. Clean data.
    4. Save clean CSV/JSON.
    5. Build Chroma index.
    6. Tao hoac load evaluation set.
    7. Evaluate.
    8. Run quality checks va freshness report.
    9. Tao markdown report.
    10. Co the demo agent tren vai sample question.
    """
    # 1. Load settings.
    settings = load_settings()
    require_llm_credentials(settings)
    paths = settings.paths

    # 2. Load hoac fetch raw records.
    if settings.refresh_source or not paths.raw_records_json.exists():
        records = fetch_source_records(settings)
        source_mode = "fetched"
    else:
        records = load_raw_records(paths.raw_records_json)
        source_mode = "loaded_snapshot"

    # 3. Clean data.
    run_date = now_utc()
    clean_df = build_clean_dataframe(records, run_date)
    if clean_df.empty:
        raise RuntimeError("Cleaning produced an empty dataframe; cannot continue Phase 1.")

    # 4. Save clean CSV/JSON.
    write_csv(clean_df, paths.clean_csv)
    write_json(paths.clean_json, clean_df.to_dict(orient="records"))

    # 5. Build Chroma index.
    index = LocalEmbeddingIndex.build(
        clean_df,
        settings=settings,
        embeddings_output_path=paths.embeddings_json,
    )

    # 6. Tao hoac load evaluation set.
    if settings.refresh_test_set or not paths.eval_testset.exists():
        test_set = build_test_set(clean_df, paths.eval_testset)
        test_set_mode = "built"
    else:
        test_set = read_json(paths.eval_testset)
        test_set_mode = "loaded"

    # 7. Evaluate.
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.baseline_metrics,
        answers_output_path=paths.baseline_answers,
    )

    # 8. Run quality checks va freshness report.
    quality = run_data_quality_checks(clean_df, settings, report_name="baseline")
    freshness = build_freshness_report(clean_df, settings, paths.freshness_report)

    # 9. Tao markdown report.
    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "source_mode": source_mode,
        "raw_record_count": len(records),
        "clean_record_count": int(len(clean_df)),
        "test_set_mode": test_set_mode,
        "test_set_size": len(test_set),
        "collection_name": settings.baseline_collection_name,
        "embedding_model": settings.embedding_model,
    }
    generate_phase1_report(
        report_path=paths.baseline_report,
        source_summary=source_summary,
        metrics=bundle.summary,
        quality=quality,
        freshness=freshness,
    )

    # 10. Co the demo agent tren vai sample question.
    demo_answers = []
    try:
        agent = build_agent(settings, index)
        sample_questions = [item["question"] for item in test_set[:3]]
        for question in sample_questions:
            demo_answers.append(
                {
                    "question": question,
                    "answer": run_agent_question(agent, question),
                }
            )
        write_json(paths.demo_answers, demo_answers)
    except Exception as exc:  # noqa: BLE001 - demo must not block baseline artifacts
        write_json(
            paths.demo_answers,
            {
                "error": f"Agent demo skipped: {exc}",
                "answers": demo_answers,
            },
        )

    print("Phase 1 baseline completed.")
    print(f"Clean records: {len(clean_df)}")
    print(f"Metrics: {paths.baseline_metrics}")
    print(f"Quality: {quality.get('success')} | Freshness: {freshness.get('is_fresh')}")
    print(f"Report: {paths.baseline_report}")
