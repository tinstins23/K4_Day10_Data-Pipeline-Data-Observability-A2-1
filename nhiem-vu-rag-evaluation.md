# Nhiệm vụ: RAG & Evaluation Engineer (Nguyễn Xuân Hùng)

Chiến lược: làm trước với **mock data** trong `data/clean/`, không phụ thuộc Thành viên 1. Khi có dữ liệu thật từ `cleaning.py`, chỉ cần thay file và chạy lại — không đổi code.

## Bước 0: Setup môi trường

- [ ] `uv sync` (hoặc `pip install -e .`)
- [ ] Copy `.env.example` → `.env`, điền `LLM_PROVIDER`/`LLM_MODEL`/API key (mặc định Gemini)
- [ ] Kiểm tra các TODO liên quan: `grep -RInE "TODO\(student\)|NotImplementedError" src/evaluation`

## Bước 1: Đọc hiểu code retrieval (src/retrieval/)

- [ ] `embeddings.py`: `MiniLMEmbeddings` bọc `sentence-transformers/all-MiniLM-L6-v2`, có `embed_documents` và `embed_query`.
- [ ] `index.py`: `LocalEmbeddingIndex` — `build()` tạo collection Chroma từ dataframe clean, `search()` trả `SearchResult(paper_id, title, score, content, metadata)`, `lookup()` tra theo `paper_id`/title chính xác.
- [ ] `qa.py`: `answer_question()` dùng `index.search()` + regex bắt title trong dấu `'...'` để trả lời theo loại câu hỏi (authors/date/categories/summary).
- [ ] `agent.py`: agent LangChain bọc 2 tool `semantic_search_papers` và `lookup_paper` trên cùng index.
- [ ] Lưu ý: `index.py` cần dataframe clean có đủ cột `paper_id, title, text_for_embedding, published, authors_joined, categories_joined, summary, abs_url, pdf_url`.

## Bước 2: Tạo mock cleaned data đúng schema

File đích: `data/clean/papers_clean.json` (đây là path thật `Settings.paths.clean_json` dùng trong pipeline, không phải file mẫu có sẵn `mock_cleaned_papers.json` — file mẫu đó thiếu `authors_joined`, `categories_joined`, `abs_url`, `pdf_url`).

Mock cần tối thiểu ~8-10 record để test set có đủ đa dạng loại câu hỏi. Mỗi record cần:

```json
{
  "paper_id": "10.xxxx/xxxxx",
  "title": "...",
  "summary": "...",
  "authors_joined": "Author A, Author B",
  "categories_joined": "Category A, Category B",
  "published": "2024-01-15",
  "age_days": 10,
  "abs_url": "https://doi.org/...",
  "pdf_url": "https://...",
  "text_for_embedding": "Title: ... | Summary: ..."
}
```

- [ ] Viết script nhỏ (VD `script/make_mock_clean.py`, không commit vào flow chính) sinh 8-10 record mock đủ field trên, ghi ra `data/clean/papers_clean.json`.

## Bước 3: Build thử index từ mock data

- [ ] Viết đoạn test thủ công (hoặc REPL) gọi `LocalEmbeddingIndex.build(df, settings)` với dataframe đọc từ mock JSON.
- [ ] Gọi `index.search("...")` và `index.lookup("...")` để chắc chắn ChromaDB + MiniLM chạy đúng trên máy mình trước khi phụ thuộc data thật.

## Bước 4: Implement `src/evaluation/testset.py`

- [ ] Hoàn thành `build_test_set(df, output_path)` theo pseudo-code có sẵn:
  - Kiểm tra `len(df)` tối thiểu (raise lỗi rõ ràng nếu quá ít record).
  - Chọn một số paper đại diện.
  - Sinh đủ 4 loại câu hỏi: `summary`, `authors`, `date`, `categories`.
  - Mỗi sample có đủ field: `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`.
  - Ghi JSON ra `output_path` (path thật: `data/eval/test_set.json`).
- [ ] Chạy thử `build_test_set` trên mock dataframe, đọc lại file JSON để review câu hỏi có hợp lý không (đặc biệt câu hỏi dạng "when was ... published" và trong dấu `'title'` để khớp regex trong `qa.py`).

## Bước 5: Chạy thử Agent + xác nhận metrics

- [ ] Dùng index mock (Bước 3) + test set mock (Bước 4), gọi `evaluate_pipeline()` trong `src/evaluation/metrics.py` (đã implement sẵn, không cần sửa).
- [ ] Kiểm tra output `data/results/baseline_metrics.json` có đủ 4 field: `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score` (và `ragas` nếu bật `RUN_RAGAS=1`).
- [ ] Nếu `judge_accuracy`/`mean_judge_score` luôn thất bại vì thiếu LLM key: kiểm tra fallback heuristic trong `_judge_answer` có kích hoạt đúng không.
- [ ] Thử chạy `agent.py` (`build_agent` + `run_agent_question`) với 1-2 câu hỏi thủ công để xác nhận tool-calling hoạt động.

## Bước 6: Thay mock bằng dữ liệu thật

Khi Thành viên 1 xong `crossref.py` + `cleaning.py`:

- [ ] Backup file mock (`papers_clean.json` → `papers_clean.mock.json`) để so sánh khi cần.
- [ ] Chạy lại pipeline thật (hoặc `script/run_phase1.py` khi Thành viên 3 ghép xong) để `data/clean/papers_clean.json` được ghi từ dữ liệu Crossref thật.
- [ ] Xóa test set cũ, chạy lại `build_test_set` trên dữ liệu thật (đặt `REFRESH_TEST_SET=1` nếu pipeline hỗ trợ).
- [ ] Build lại index trên dữ liệu thật, chạy lại `evaluate_pipeline`, so sánh 4 metric với lần chạy mock — số liệu nên hợp lý hơn.

## Bước 7: Kiểm tra cuối / verification

- [ ] `data/eval/test_set.json` có đủ 4 loại câu hỏi, không rỗng field nào.
- [ ] `data/results/baseline_metrics.json` và `baseline_answers.json` khớp với test set thật (không còn dấu vết mock).
- [ ] Chạy full `uv run python script/run_phase1.py` end-to-end không lỗi.
- [ ] Báo cho Thành viên 3 để đưa số liệu vào `data/reports/phase1_report.md`, và cho Thành viên 4 để dùng làm baseline so sánh với corrupted/repaired.
