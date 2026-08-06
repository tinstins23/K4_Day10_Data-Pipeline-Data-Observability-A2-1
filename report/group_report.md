# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                                                                               |
| ------------------ |----------------------------------------------------------------------------------------|
| Khóa/Lớp         | K4                                                                                     |
| Tên nhóm         | A2-1                                                                                   |
| Repository         | https://github.com/tinstins23/K4_Day10_Data-Pipeline-Data-Observability-A2-1/tree/main |
| Ngày hoàn thành | 2026-08-06                                                                             |

### Thành viên và phân công

| STT | Họ và tên         | MSSV        | Vai trò chính | Module/deliverable sở hữu |
| --: |-------------------|-------------|----|----|
| 1 | Nguyễn Xuân Hùng  | 2A202601640 | RAG & Evaluation Engineer, tích hợp nhánh | `src/retrieval/qa.py`, `src/retrieval/llm.py`, `src/evaluation/metrics.py`, review `src/evaluation/testset.py`; merge code của 3 thành viên còn lại về nhánh chung |
| 2 | Hoàng Minh Quân   | 2A202601574 | Data Engineer | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py` |
| 3 | Hồ Trung Tín      | 2A202601688 | Observability Engineer | `src/evaluation/testset.py` (bản gốc), `src/observability/quality.py`, `src/observability/reporting.py`, `src/pipelines/phase1.py` |
| 4 | Nguyễn Mạnh Thắng | 2A202601944 | Chaos & Reliability Engineer | `src/ingestion/corruption.py`, `src/pipelines/corruption_flow.py`, `script/run_corruption_flow.py` |

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành toàn bộ 2 pha của bài lab: baseline pipeline (Crossref → clean → embedding → evaluation → quality/freshness → report) và corruption flow (corrupt → re-evaluate → repair → so sánh 3 trạng thái). Baseline lấy 24 record thật từ Crossref, tạo test set 24 câu hỏi (summary/authors/date), đạt `retrieval_hit_rate = 1.0`, `mean_token_f1 = 1.0`, `judge_accuracy = 1.0`, `mean_judge_score = 5` sau khi sửa 2 lỗi tích hợp (xem Mục 11). Thắng đã tạo 6 kịch bản corruption (xóa record mới nhất, blank summary, thêm noise, truncate title, làm cũ ngày xuất bản, duplicate) tác động lên 18/24 record. Corruption làm giảm rõ rệt các chỉ số: `retrieval_hit_rate` còn 0.625, `mean_token_f1` còn 0.503, `judge_accuracy` còn 0.5, đồng thời 4/7 data quality check chuyển sang fail (duplicate paper_id, blank/short summary, stale rows). Sau khi repair lại từ `data/raw/` bằng đúng logic cleaning của Quân, toàn bộ 4 metric và quality/freshness check phục hồi về chính xác giá trị baseline. Blocker còn lại: câu hỏi loại `categories` không sinh được (0/24) vì trường `categories` từ Crossref phần lớn rỗng với query hiện tại; Ragas chưa bật (`RUN_RAGAS=1`) do tốn thời gian chạy.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API (agentic retrieval augmented generation large language model)
    -> raw response/raw records (data/raw/)
    -> cleaning và data modeling (data/clean/)
    -> embedding (MiniLM) + ChromaDB index (data/embeddings/, data/chroma/)
    -> evaluation baseline (data/eval/, data/results/baseline_*.json)
    -> quality/freshness reports (data/quality/)
    -> corruption (6 kịch bản, data/results/corruption_log.json)
    -> re-index và re-evaluate trên dữ liệu corrupted
    -> repair từ data/raw/ (dùng lại cleaning.py)
    -> comparison report (data/reports/corruption_report.md)
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref REST API (`api.crossref.org/works`) | Fetch với retry/backoff cho 429/503, parse thành `PaperRecord` | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Hoàng Minh Quân |
| Cleaning          | `PaperRecord` thô | Chuẩn hóa title/summary/authors/categories, tính `age_days`, ghép `text_for_embedding` | `data/clean/papers_clean.csv`, `papers_clean.json` | Hoàng Minh Quân |
| Embedding/index   | Cleaned dataframe | `sentence-transformers/all-MiniLM-L6-v2` + ChromaDB collection | `data/embeddings/papers_embeddings.json`, `data/chroma/` | Hồ Trung Tín (orchestration), code tham khảo có sẵn |
| Evaluation        | Cleaned dataframe | Sinh 24 câu hỏi (summary/authors/date), chạy agent qua `qa.py`, chấm bằng LLM judge (DeepSeek) | `data/eval/test_set.json`, `data/results/baseline_*.json` | Hồ Trung Tín (testset), Nguyễn Xuân Hùng (fix qa.py + judge) |
| Observability     | Cleaned/corrupted/repaired dataframe | Data quality checks (completeness/uniqueness/validity/freshness) | `data/quality/*.json` | Hồ Trung Tín |
| Corruption/repair | Cleaned dataframe baseline | 6 kịch bản corrupt, repair lại từ `data/raw/` | `data/clean/papers_clean_corrupted.json`, `papers_clean_repaired.json`, `data/results/corruption_log.json` | Nguyễn Mạnh Thắng |
| Orchestration     | Toàn bộ module trên | Ghép luồng Pha 1 và Pha 2, đảm bảo dùng chung test set | `data/reports/phase1_report.md`, `corruption_report.md` | Hồ Trung Tín (Pha 1), Nguyễn Mạnh Thắng (Pha 2) |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | `custom` (DeepSeek qua endpoint tương thích OpenAI) |
| `LLM_MODEL`                | `deepseek-v4-flash` |
| Embedding model              | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 (`max_results=24`) |
| Retrieval`top_k`           | 4 |
| Freshness threshold          | 180 ngày |
| Random seed, nếu có        | Không áp dụng (không sampling ngẫu nhiên có seed) |

### Lệnh cài đặt

```bash
uv sync
```

### Lệnh chạy

Baseline:

```bash
uv run python script/run_phase1.py
```

Corruption flow:

```bash
uv run python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái                                    | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công | 2026-08-06 16:19 | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow   | Thành công | 2026-08-06 16:35 | `data/results/corruption_log.json`, `corrupted_metrics.json`, `repaired_metrics.json` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API — `https://api.crossref.org/works` |
| Query/filter                | `query=agentic retrieval augmented generation large language model`; `filter=from-pub-date:<180 ngày trước>,has-abstract:true` |
| Thời điểm lấy dữ liệu | 2026-08-06 |
| Số record nhận được    | 24 |
| Cơ chế retry/backoff      | Retry khi gặp HTTP 429/503 (rate limit/lỗi tạm thời) trước khi lưu raw response |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id`    | string (DOI)   | Có        | Định danh duy nhất của bài báo | Loại record nếu thiếu DOI |
| `title`       | string         | Có        | Tiêu đề bài báo | Loại record nếu rỗng |
| `summary`     | string         | Có        | Abstract | Loại record nếu rỗng |
| `authors_joined` | string (nối bằng `, `) | Không | Danh sách tác giả dạng text | Ghi `"Unknown authors"` nếu rỗng khi sinh câu hỏi |
| `categories_joined` | string | Không | Chủ đề/lĩnh vực | Thường rỗng với Crossref (không phải mọi record có `subject`) |
| `published`   | string (YYYY-MM-DD) | Có   | Ngày xuất bản | Dùng để tính `age_days` |
| `age_days`    | int            | Có (suy ra) | Độ tuổi bài báo tính từ ngày chạy pipeline | Tính lại khi repair/corrupt ngày xuất bản |
| `text_for_embedding` | string  | Có (suy ra) | Chuỗi ghép title+summary dùng để encode vector | Rebuild lại mỗi khi title/summary thay đổi (kể cả sau corruption) |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Số record bị tác động | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Loại record thiếu `paper_id`/`title`/`summary` | Completeness | 0/24 (dataset nguồn đã sạch) | `data/quality/baseline_quality.json` — `paper_id_not_null`, `title_not_null` đều pass |
| Chuẩn hóa `authors`/`categories` thành chuỗi nối `, ` | Validity | 24/24 | So khớp `authors_joined` với câu trả lời `qa.py` cho câu hỏi loại `authors` |
| Yêu cầu `summary` tối thiểu 40 ký tự | Validity | 0/24 vi phạm | `summary_min_length` trong `baseline_quality.json` (min thực tế 834 ký tự) |
| Tính `age_days` từ `published` so với ngày chạy pipeline | Freshness | 24/24 | `freshness_report.json` — max_age_days 175 ngày (dưới ngưỡng 180) |

Cách tạo `text_for_embedding`, document ID và `age_days`:

`paper_id` dùng trực tiếp DOI trả về từ Crossref làm document ID ổn định xuyên suốt baseline/corrupted/repaired. `text_for_embedding` được ghép theo mẫu `"Title: {title} | Summary: {summary}"` — khi corruption sửa title (truncate) hoặc summary (blank/noise), cột này được rebuild lại để index phản ánh đúng nội dung đã bị hỏng, đảm bảo tác động corruption được lan tới tận bước embedding chứ không chỉ dừng ở data quality check. `age_days` = số ngày giữa `published` và thời điểm chạy pipeline; khi corruption làm cũ ngày xuất bản (`make_published_date_stale`, đặt về `2000-01-01`), `age_days` được tính lại nên freshness check phát hiện đúng 3 record trở nên stale.

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 24 |
| Các`question_type`                    | `summary` (8), `authors` (8), `date` (8) — `categories` không sinh được vì `categories_joined` rỗng ở phần lớn record nguồn |
| Ground-truth document ID                 | Chính `paper_id` của record dùng để sinh câu hỏi |
| Embedding model                          | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection                  | ChromaDB, collection `papers-baseline` / `papers-corrupted` / `papers-repaired` |
| Retrieval`top_k`                       | 4 |
| LLM provider/model                       | `custom` provider → DeepSeek `deepseek-v4-flash` (non-thinking mode, xem Mục 11) |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` (không regenerate giữa baseline/corrupted/repaired) |

Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:

`refresh_test_set` mặc định `False` và `corruption_flow.py` chỉ đọc `settings.paths.eval_testset` đã tồn tại từ Pha 1, không sinh lại câu hỏi mới. Nếu regenerate test set trên dữ liệu đã corrupt, ground truth sẽ bị nhiễm theo lỗi (ví dụ sinh câu hỏi từ summary đã bị làm rỗng), khiến phép so sánh baseline/corrupted/repaired mất ý nghĩa. Giữ cố định 1 bộ 24 câu hỏi đảm bảo cả 3 lần evaluate đo cùng một "đề thi".

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/`                          | Có | 24 record, retry/backoff hoạt động (không log lỗi 429/503 ở lần chạy cuối) |
| Cleaned dataset          | `data/clean/`                        | Có | 24 record, đủ 16 cột schema |
| Embedding manifest/index | `data/embeddings/`                   | Có | `papers_embeddings.json` + ChromaDB tại `data/chroma/` |
| Evaluation set           | `data/eval/`                         | Có | 24 câu hỏi |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có | Xem bảng dưới |
| Quality/freshness        | `data/quality/`                      | Có | `baseline_quality.json`, `freshness_report.json` |
| Baseline report          | `data/reports/phase1_report.md`      | Có | Khớp với `baseline_metrics.json` |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` |     1.0 | Cả 24/24 câu, tài liệu đúng nằm trong top-4 kết quả retrieval |
| `mean_token_f1`      |     1.0 | Câu trả lời rule-based (`qa.py`) khớp tuyệt đối ground truth sau khi sửa lỗi nhận diện câu hỏi (Mục 11) |
| `judge_accuracy`     |     1.0 | DeepSeek chấm đúng ("correct") cho toàn bộ 24 câu |
| `mean_judge_score`   |     5.0 | Điểm tối đa trên thang 1–5 |
| Ragas, nếu có        | Bỏ qua | Chưa bật `RUN_RAGAS=1` vì thời gian chạy lâu hơn đáng kể (mỗi câu cần thêm nhiều lệnh gọi LLM) |

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline      | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| `row_count_positive` | Completeness | > 0 | Pass (24) | `baseline_quality.json` |
| `paper_id_not_null` / `paper_id_unique` | Completeness/Uniqueness | 0 record thiếu/trùng | Pass (0/0) | `baseline_quality.json` |
| `title_not_null` | Completeness | 0 record thiếu | Pass (0) | `baseline_quality.json` |
| `summary_min_length` | Validity | ≥ 40 ký tự | Pass (min 834, median 1661) | `baseline_quality.json` |
| `freshness_age_days` | Freshness | `age_days` ≤ 180 | Pass (max 175) | `baseline_quality.json` |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | `data/clean/papers_clean.json` (24 record) |
| Timestamp mới nhất       | `2026-08-01` |
| Ngưỡng freshness         | 180 ngày |
| Trạng thái baseline      | Fresh (`is_fresh: true`, 0 record stale, mean_age_days ≈ 76.6) |
| Lý do                     | Toàn bộ 24 record có `age_days` ≤ 175, dưới ngưỡng 180 |

## 9. Corruption scenarios và repair

| Corruption         | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair   |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| `delete_newest_records` | Xóa 3 record có `published` mới nhất | 3 | Giảm coverage & freshness | `output_rows` không đổi (24) vì bù lại bởi duplicate; `latest_published` tụt từ `2026-08-01` xuống `2026-07-10` | Đọc lại `data/raw/`, clean lại toàn bộ |
| `blank_summary` | Xóa nội dung summary | 3 | Giảm completeness | `summary_not_blank` fail (6 — trùng với record bị noise) | Rebuild từ raw summary gốc |
| `inject_text_noise` | Chèn chuỗi `"@@@ CORRUPTED_NOISE_9F3A ### xqzv 000111 !!!"` vào summary | 3 | Retrieval kém ổn định | Góp phần kéo `mean_token_f1` xuống 0.503 | Rebuild `text_for_embedding` từ raw |
| `truncate_title` | Cắt title còn tối đa 12 ký tự | 3 | Title lookup/retrieval kém hơn | Ảnh hưởng câu hỏi dùng exact-title lookup trong `qa.py` | Khôi phục title đầy đủ từ raw |
| `make_published_date_stale` | Đặt `published = 2000-01-01` | 3 | Freshness check phát hiện stale | `freshness_threshold` fail, `stale_rows = 3` | Tính lại `published`/`age_days` từ raw |
| `duplicate_records` | Nhân đôi 3 record | 3 (bản sao) | Uniqueness check fail | `paper_id_unique` fail, `duplicate_paper_ids = 3` | Dedupe khi rebuild từ raw |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log đủ 6 loại corruption, mỗi loại ghi rõ `affected_count`, danh sách `paper_ids` bị tác động và `expected_effect`; tổng 18/24 record (một số bị hơn 1 corruption) bị tác động, `net_row_change = 0`.

Giải thích cách repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy thay vì chỉ che kết quả lỗi:

Repair không sửa trực tiếp trên dataframe đã corrupt. `corruption_flow.py` đọc lại `data/raw/crossref_records.json` (raw records gốc, không bị corruption chạm tới) và chạy lại đúng `build_clean_dataframe()` của Quân để tái tạo `papers_clean_repaired.json` từ đầu. Vì vậy repaired data không chỉ "trông giống" baseline mà **giống hệt** baseline: `repaired_quality.json` pass 7/7 check với `details` toàn 0, và `repaired_freshness.json` khớp chính xác `freshness_report.json` gốc (`latest_published: 2026-08-01`, `stale_rows: 0`).

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   |     1.0 |     0.625 |     1.0 | -0.375 (-37.5%) | 100% | Noise + truncate title làm embedding/lookup lệch, đủ để tài liệu đúng rớt khỏi top-4 ở 9/24 câu |
| `mean_token_f1`        |     1.0 |    0.5028 |     1.0 | -0.4972 | 100% | Trả lời rỗng/sai do summary bị blank hoặc noise |
| `judge_accuracy`       |     1.0 |       0.5 |     1.0 | -0.5 | 100% | DeepSeek chấm "không đúng" cho các câu có answer rỗng hoặc lệch nội dung |
| `mean_judge_score`     |     5.0 |    3.0833 |     5.0 | -1.9167 | 100% | Điểm trung bình giảm gần 2 điểm/5 |
| Quality checks pass/fail |     Pass (7/7) |     Fail (3/7 fail: uniqueness, summary, freshness) |     Pass (7/7) | 4 check chuyển fail | 100% | `paper_id_unique`, `summary_not_blank`, `summary_min_length`, `freshness_threshold` |
| Freshness status         |     Fresh |     Stale (3 record) |     Fresh | +3 stale rows | 100% | `make_published_date_stale` đặt về năm 2000 |

Hai kết luận nhân quả:

1. `blank_summary` + `inject_text_noise` + `truncate_title` → `summary_not_blank`/`summary_min_length` fail và `text_for_embedding` bị hỏng nội dung → `retrieval_hit_rate` giảm còn 0.625 và `mean_token_f1` giảm còn 0.503 vì agent trích câu trả lời từ metadata đã bị corrupt.
2. Repair đọc lại từ `data/raw/` và chạy lại `cleaning.py` gốc → toàn bộ 7/7 quality check pass, freshness trở lại fresh → cả 4 metric agent (`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score`) phục hồi về đúng giá trị baseline (1.0/1.0/1.0/5), chứng minh repair khôi phục thật sự chứ không che giấu lỗi.

Không có kết quả nào khác kỳ vọng ban đầu — mức độ giảm và phục hồi đều khớp với thiết kế 6 kịch bản corruption.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Sau khi chạy `run_phase1.py` lần đầu, `baseline_metrics.json` cho `judge_accuracy`/`mean_judge_score` nhìn hợp lý, nhưng `data/results/baseline_answers.json` cho thấy **24/24 câu đều có `judge.reasoning = "Fallback heuristic judge used because the LLM evaluator was unavailable."`** — nghĩa là LLM judge chưa từng chạy thật, `_judge_answer()` trong `metrics.py` âm thầm nuốt lỗi (`except Exception`) và rơi về heuristic dựa trên `token_f1`.
- **Nguyên nhân:** Gồm 2 lỗi chồng lên nhau. (1) `LLM_MODEL=gemini-2.5-flash` bị Google trả về `404 NOT_FOUND` vì model này ngừng cấp cho user mới từ 9/7/2026. (2) Sau khi đổi sang provider DeepSeek (`deepseek-v4-flash`, dùng nhánh `custom` trong `retrieval/llm.py`), `with_structured_output()` tiếp tục lỗi `400` hai lần: đầu tiên do `response_format` kiểu `json_schema` không được DeepSeek hỗ trợ, sau khi đổi `method="function_calling"` thì gặp lỗi `"Thinking mode does not support this tool_choice"` vì DeepSeek bật "thinking mode" mặc định, không cho ép `tool_choice` về một hàm cụ thể.
- **Cách xử lý:** Đổi `LLM_MODEL` sang `deepseek-v4-flash` qua provider `custom`; sửa `_judge_answer()` trong `src/evaluation/metrics.py` dùng `with_structured_output(JudgeVerdict, method="function_calling")`; thêm `extra_body={"thinking": {"type": "disabled"}}` vào nhánh `custom` trong `src/retrieval/llm.py` để tắt thinking mode. Đồng thời phát hiện và sửa thêm 1 lỗi độc lập trong `src/retrieval/qa.py`: điều kiện nhận diện câu hỏi loại `authors`/`categories` chỉ khớp cụm `"who authored"`/`"what categories"`, không khớp cách hỏi thực tế của `testset.py` (`"who are the authors"`), khiến toàn bộ câu hỏi `authors` bị trả lời sai bằng đoạn summary.
- **Cách xác minh:** Viết `script/debug_judge.py` gọi thẳng `build_llm(...).with_structured_output(...)` không bọc try/except để lộ traceback thật thay vì bị `metrics.py` nuốt lỗi. Sau khi sửa, chạy lại `run_phase1.py` và `grep -c "Fallback heuristic" data/results/baseline_answers.json` trả về `0`, đồng thời `judge.reasoning` chứa câu văn LLM thật sinh ra (ví dụ: "The model answer exactly matches the reference answer, correctly identifying...").

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Câu hỏi loại `categories` không sinh được (0/24) vì `categories_joined` rỗng ở đa số record Crossref | Bộ test set thiếu 1/4 loại câu hỏi dự kiến, giảm độ phủ đánh giá | Đổi `source_query`/`source_filter` để ưu tiên record có `subject`, hoặc fallback dùng `primary_category` khi `categories_joined` rỗng — đo lại bằng `Counter(question_type)` trên `test_set.json` |
| Ragas chưa được bật (`RUN_RAGAS=1`) | Thiếu 4 chỉ số bổ sung (`answer_relevancy`, `context_precision`, `context_recall`, `faithfulness`) mà Rubric có tính bonus | Chạy `RUN_RAGAS=1 uv run python script/run_phase1.py` một lần, so metric bổ sung với 4 metric chính hiện có |
| `except Exception` trong `_judge_answer()` nuốt lỗi âm thầm, từng khiến 24/24 câu dùng fallback mà không có cảnh báo rõ ràng | Rủi ro báo cáo sai số liệu nếu không kiểm tra `baseline_answers.json` thủ công | Log lại exception (ví dụ ra `data/results/judge_errors.log`) thay vì chỉ fallback im lặng, để phát hiện sớm hơn ở lần chạy sau |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set (`data/eval/test_set.json`).
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên có báo cáo vai trò riêng (xem `report/2A202601640_NguyenXuanHung.md`; các thành viên khác tự bổ sung theo cùng quy ước `<MSSV>_HoTen.md`).
- [x] Không có `.env`, API key, token hoặc secret trong repository, report hoặc log.
