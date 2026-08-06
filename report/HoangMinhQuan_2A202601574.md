# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Hoàng Minh Quân          |
| MSSV               | 2A202601574                |
| Khóa/Lớp         | K4                        |
| Tên nhóm         | Day10 Data Pipeline A2     |
| Vai trò chính    | Thành viên 1 — Data Engineer (Thu thập & Làm sạch dữ liệu) |
| Repository         | https://github.com/tinstins23/K4_Day10_Data-Pipeline-Data-Observability-A2-1 |
| Ngày hoàn thành | 2026-08-06                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Crossref ingestion | `src/ingestion/crossref.py` — `fetch_source_records`, `_request_with_retry`, `parse_crossref_payload`, `load_raw_records` | Crossref API (`/works`), `Settings` (query/filter/rows) | `data/raw/crossref_response.json`, `data/raw/crossref_records.json`, `list[PaperRecord]` | Hoàn thành |
| Data cleaning | `src/ingestion/cleaning.py` — `build_clean_dataframe` | `list[PaperRecord]`, `run_date` | DataFrame sạch → `data/clean/papers_clean.csv`, `papers_clean.json` | Hoàn thành |

Phần việc của tôi là **mốc hoàn thành đầu tiên**: cung cấp dữ liệu sạch, truy vết được, để các thành viên còn lại làm embedding, agent, evaluation và observability.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Giải thích schema `PaperRecord` và ý nghĩa `text_for_embedding` / `age_days` | Thành viên embedding & RAG | Nhóm dùng đúng cột khi build Chroma index |
| Demo UI pipeline Member 1 (tùy chọn) | Cả nhóm khi thuyết trình | Trang web xem raw/clean tại `ui/` |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Gọi Crossref API + retry/backoff khi 429/503 | `crossref.py` → `_request_with_retry`, `fetch_source_records` | Raw response 24 items | File `data/raw/crossref_response.json` có `"status": "ok"` |
| Lưu raw để truy vết | `write_json` vào paths trong `config.py` | `crossref_response.json` + `crossref_records.json` | Kiểm tra thư mục `data/raw/` |
| Parse về schema thống nhất | `parse_crossref_payload`, `PaperRecord` | 24 records đã parse | `load_raw_records` đọc lại được |
| Cleaning: chuẩn hóa, lọc lỗi, `text_for_embedding`, `age_days` | `cleaning.py` → `build_clean_dataframe` | 24 dòng sạch | `papers_clean.csv` có đủ cột helper |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Đã bàn giao **24 papers sạch** trong `data/clean/papers_clean.csv` (và JSON tương ứng), kèm raw gốc trong `data/raw/` để nhóm có thể repair từ nguồn khi dữ liệu bị corrupt. Đây là đầu vào trực tiếp cho bước embedding/Chroma.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline RAG cần corpus học thuật ổn định. Nếu chỉ gọi API rồi dùng luôn response thô thì:

- không truy vết được khi dữ liệu lỗi,
- schema Crossref không đồng nhất (title là list, abstract có HTML/JATS, ngày dạng `date-parts`),
- thiếu cột sẵn sàng cho embedding và freshness (`text_for_embedding`, `age_days`).

Vai trò Data Engineer giải quyết đoạn **Crossref → raw → clean**.

### Cách triển khai

1. **Fetch:** `GET https://api.crossref.org/works` với `query`, `filter` (`from-pub-date`, `has-abstract:true`), `rows=24` lấy từ `Settings`.
2. **Retry/backoff:** nếu status `429`/`503` thì sleep theo `Retry-After` hoặc exponential backoff (`1.5 * 2^attempt`), tối đa 5 lần.
3. **Lưu raw response nguyên bản** → `data/raw/crossref_response.json` (không chỉnh sửa).
4. **Parse:** map từng item → `PaperRecord` (DOI→`paper_id`, abstract→`summary`, authors, subjects, published…). Bỏ item thiếu DOI/title/abstract; strip markup HTML/JATS.
5. **Lưu raw records đã parse** → `data/raw/crossref_records.json`.
6. **Cleaning:** chuẩn hóa whitespace; parse ngày; tính `age_days`; tạo `authors_joined`, `categories_joined`, `summary_chars`, `text_for_embedding`; drop trùng `paper_id`; lọc summary quá ngắn; sort theo `published` mới nhất.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Crossref JSON; hoặc snapshot `crossref_records.json` khi không gọi lại API |
| Output                         | `PaperRecord` / DataFrame với `paper_id`, `title`, `summary`, `text_for_embedding`, `age_days`, URL… |
| Module phụ thuộc             | `core.config.Settings`, `core.utils` (`write_json`, `normalize_whitespace`) |
| Module sử dụng output        | Embedding/index (`LocalEmbeddingIndex`), evaluation, quality/freshness, corruption/repair |
| Điều kiện lỗi cần xử lý | Rate-limit 429/503; item thiếu abstract; ngày không parse được; trùng DOI |

### Cách xác minh

```powershell
python -c "from core.config import load_settings; from core.utils import now_utc; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); r=load_raw_records(s.paths.raw_records_json); df=build_clean_dataframe(r, now_utc()); print(len(r), len(df), list(df.columns))"
```

- **Kết quả mong đợi:** `records > 0`, `clean_rows > 0`, có cột `text_for_embedding` và `age_days`, không `NotImplementedError`.
- **Kết quả thực tế:** `records 24`, `clean_rows 24`, đủ cột helper; raw/clean files tồn tại trong `data/`.
- **Artifact/log:** `data/raw/crossref_response.json`, `data/raw/crossref_records.json`, `data/clean/papers_clean.csv`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần tách “bằng chứng gốc từ API” và “bản đã chuẩn hóa cho pipeline”.
- **Các phương án đã cân nhắc:**
  1. Chỉ lưu cleaned CSV, bỏ raw response.
  2. Lưu cả raw response gốc và raw records đã parse trước khi clean.
- **Phương án đã chọn:** Phương án 2 — đúng Guide/README và path trong `config.py`.
- **Lý do:** Raw gốc đảm bảo **reproducibility/traceability**; raw records là contract ổn định cho cleaning; khi corruption xảy ra có thể **repair từ raw** mà không phụ thuộc API lúc đó còn trả cùng kết quả.
- **Bằng chứng quyết định phù hợp:** Có đủ `data/raw/*` và `data/clean/*`; flow repair của nhóm dùng lại dữ liệu sạch từ nguồn raw/clean đã lưu.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Crossref có thể trả `429`/`503` khi bị rate-limit hoặc lỗi tạm thời (README cũng cảnh báo).
- **Lệnh hoặc bước tái hiện:** Gọi liên tục `fetch_source_records(load_settings())` khi API quá tải.
- **Nguyên nhân gốc:** Client gọi API công khai không có cơ chế chờ/thử lại sẽ fail cứng ở lần lỗi tạm thời.
- **Cách xử lý:** Implement `_request_with_retry` với tập status `{429, 503}`, tôn trọng header `Retry-After` nếu có, không thì exponential backoff.
- **Cách xác minh sau khi sửa:** Fetch thành công, ghi được `crossref_response.json` với `"status": "ok"` và 24 items.
- **Điều học được:** Với API ngoài, retry/backoff và lưu raw là hai lớp bảo vệ khác nhau: một cái chống lỗi tạm thời, một cái chống mất khả năng truy vết.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Crossref → vector index:** API `/works` → lưu raw response/records → `cleaning.py` tạo bảng sạch có `text_for_embedding` → embedding MiniLM → nạp ChromaDB (collection baseline).  
2. **Evaluation set:** tạo câu hỏi từ cleaned data; mỗi sample có `question`, `ground_truth`, `ground_truth_doc_ids`, `question_type`. Khi evaluate, retrieval xem `paper_id` trả về có khớp `ground_truth_doc_ids` không (hit rate), câu trả lời so với ground truth (token F1 / judge).  
3. **Quality vs freshness:** quality check schema/nội dung (null id, trùng DOI, title/summary trống, độ dài summary…); freshness theo `age_days`/ngày published so với ngưỡng (180 ngày) để biết dữ liệu có bị “già” không.  
4. **Cùng test set cho baseline/corrupted/repaired:** để so sánh công bằng — thay đổi metrics phản ánh chất lượng dữ liệu, không phải do đổi bộ câu hỏi.  
5. **Repair thành công khi:** dataset repaired gần/khớp baseline (ví dụ quality `passed=true`, freshness `is_fresh=true`) và metrics agent phục hồi về mức baseline (hit rate, F1, judge).

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      1.0 |     0.625 |      1.0 | Corrupt làm retrieval kém rõ; repair lấy lại baseline |
| `mean_token_f1`      |      1.0 |     0.503 |      1.0 | Summary/title bị nhiễu ảnh hưởng câu trả lời |
| `judge_accuracy`     |      1.0 |       0.5 |      1.0 | Judge xác nhận chất lượng trả lời giảm khi data xấu |
| `mean_judge_score`   |        5 |     3.083 |        5 | Điểm tuyệt đối cũng phục hồi sau repair |
| Quality checks         |   pass*  |      fail |     pass | Corrupted: trùng DOI, summary trống/ngắn, stale |
| Freshness status       |  fresh*  | not fresh |    fresh | Corrupted có `stale_rows=3`, oldest đẩy về `2000-01-01` |

\*Baseline quality/freshness đi cùng corpus sạch Member 1 bàn giao; số liệu corrupted/repaired lấy từ `data/quality/*` và `data/results/*`.

### Kết luận từ số liệu

1. **Blank/noise summary + duplicate + stale date** → quality `passed=false`, freshness `is_fresh=false` → `retrieval_hit_rate` 1.0→0.625, `mean_token_f1` 1.0→0.503, judge giảm.  
2. **Repair từ raw/clean gốc** → quality/freshness pass trở lại → metrics agent về 1.0 / score 5 như baseline.

Corruption nào ảnh hưởng rõ nhất và vì sao?

Các lỗi làm **hỏng `text_for_embedding`/summary** và **duplicate/stale** ảnh hưởng mạnh vì retrieval và trả lời đều dựa trên text đã embed; thiếu/nhiễu summary làm context sai, duplicate làm id không unique, stale làm freshness fail.

Kết quả nào khác với kỳ vọng ban đầu?

Kỳ vọng corrupt chỉ làm giảm nhẹ; thực tế hit rate còn 0.625 và judge_accuracy còn 0.5 — mức giảm lớn, chứng minh data quality không phải “phụ” mà là điều kiện để RAG ổn định. Repair phục hồi gần như hoàn toàn là đúng kỳ vọng khi còn raw đầy đủ.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Pipeline phải có **lớp raw bất biến** trước khi clean; đó là nền cho debug và repair.  
2. Cleaning không chỉ “cho đẹp” — cột như `text_for_embedding` và `age_days` quyết định retrieval và observability phía sau.  
3. Metrics agent (hit rate, F1, judge) **đi xuống khi data xấu và đi lên khi repair** → chất lượng dữ liệu ảnh hưởng trực tiếp chất lượng RAG.

### Nếu có thêm thời gian

Thêm validation tự động sau mỗi lần fetch (số record tối thiểu, tỷ lệ có abstract, phân bố `age_days`) và fail sớm nếu raw không đạt ngưỡng — đo bằng tỷ lệ lần fetch phải gọi lại API / số lần quality fail trước embedding.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Hoàng Minh Quân  
**Ngày xác nhận:** 2026-08-06
