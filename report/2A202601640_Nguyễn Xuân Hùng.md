# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Xuân Hùng         |
| MSSV               | 2A202601640                 |
| Khóa/Lớp         | K4                         |
| Tên nhóm         | A2-1                       |
| Vai trò chính    | RAG & Evaluation Engineer, tích hợp code toàn nhóm |
| Repository         | https://github.com/tinstins23/K4_Day10_Data-Pipeline-Data-Observability-A2-1/tree/main |
| Ngày hoàn thành | 2026-08-06                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Đọc/hiểu retrieval | `src/retrieval/embeddings.py`, `index.py`, `qa.py`, `agent.py` | Cleaned dataframe từ Quân | Xác nhận MiniLM + ChromaDB hoạt động đúng trước khi phase1.py có sẵn | Hoàn thành |
| Fix nhận diện câu hỏi QA | `src/retrieval/qa.py` — `_extract_answer()` | Câu hỏi text từ `testset.py` | Nhận đúng loại câu hỏi `authors`/`categories` thay vì mặc định trả về summary | Hoàn thành |
| Tích hợp LLM judge dùng được | `src/retrieval/llm.py`, `src/evaluation/metrics.py` | `Settings` (provider/model/API key) | LLM judge chạy thật qua DeepSeek, không còn fallback heuristic | Hoàn thành |
| Debug tooling | `script/debug_judge.py`, `script/build_index_manual.py` | — | Script tái hiện lỗi LLM judge và build index thủ công trước khi `phase1.py` sẵn sàng | Hoàn thành |
| Tích hợp code 3 nhánh | Merge `quanhm`, `tin/dev`, `Thang` vào `NguyenXuanHung` | Code độc lập của từng thành viên | Nhánh hợp nhất chạy được end-to-end cả Pha 1 và Pha 2 | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Resolve conflict `cleaning.py`/`crossref.py` (giữ bản của Quân) | Hoàng Minh Quân | Merge `quanhm` sạch, không mất logic cleaning/ingestion |
| Resolve conflict `testset.py`/`quality.py`/`reporting.py` (giữ bản của Tín) | Hồ Trung Tín | Merge `tin/dev` và `Thang` không đè mất `phase1.py` orchestration đã verify |
| Chạy thử `run_phase1.py` và `run_corruption_flow.py` sau mỗi lần merge | Cả nhóm | Phát hiện 2 lần merge bị `git reset` nhầm làm mất code của Thắng trước khi commit đúng cách |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Sửa `_extract_answer()` nhận nhầm câu hỏi `authors` thành summary | `src/retrieval/qa.py` | `mean_token_f1` tăng từ 0.667 lên 1.0 | So sánh `data/results/baseline_answers.json` trước/sau fix, kiểm tra 8 câu `question_type: authors` |
| Chuyển LLM judge từ Gemini (404, hết quota) sang DeepSeek hoạt động ổn định | `src/retrieval/llm.py`, `.env` | `judge_accuracy = 1.0`, `mean_judge_score = 5.0` với reasoning do LLM thật sinh ra | `grep -c "Fallback heuristic" data/results/baseline_answers.json` → `0` |
| Merge tuần tự 3 nhánh (`quanhm` → `tin/dev` → `Thang`) vào nhánh làm việc | `.git` history, `git log --oneline --all --graph` | Nhánh `NguyenXuanHung` chứa đủ code của cả 4 thành viên, không còn `NotImplementedError` | `grep -RInE "raise NotImplementedError" src` → không có kết quả |
| Xác nhận Pha 2 chạy đúng trên code đã merge | `data/results/corrupted_metrics.json`, `repaired_metrics.json` | Baseline → Corrupted → Repaired: 1.0 → 0.625 → 1.0 (`retrieval_hit_rate`) | `uv run python script/run_corruption_flow.py`, đọc lại 3 file metrics |

Output cụ thể: file `data/results/baseline_metrics.json` sau khi tôi sửa `qa.py` và `llm.py` đổi từ `{"retrieval_hit_rate": 1.0, "mean_token_f1": 0.667, "judge_accuracy": 0.667 (giả, do fallback), "mean_judge_score": 3.67 (giả)}` thành `{"retrieval_hit_rate": 1.0, "mean_token_f1": 1.0, "judge_accuracy": 1.0, "mean_judge_score": 5.0}` với judge thật.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Sau khi Pha 1 chạy được lần đầu, số liệu "trông ổn" nhưng không đáng tin: cần xác minh hệ thống evaluation (`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score`) tính đúng bản chất chứ không phải trùng hợp hoặc dùng nhánh fallback. Ngoài ra cần đưa code của 4 thành viên (độc lập phát triển trên các nhánh khác nhau) về một nhánh chạy được end-to-end mà không ai mất công sức.

### Cách triển khai

Với `qa.py`: đối chiếu từng câu hỏi trong `data/results/baseline_answers.json` có `token_f1 = 0.0` với `retrieved_doc_ids` — phát hiện tài liệu retrieval đúng (`retrieved_doc_ids[0] == ground_truth_doc_ids[0]`) nhưng answer lại là đoạn summary, tức lỗi nằm ở khâu chọn field trả lời chứ không phải retrieval. Mở rộng điều kiện `if "author" in lowered` và `if "categor" in lowered or "subject" in lowered` thay vì so khớp cụm cố định.

Với LLM judge: dùng phương pháp loại trừ — viết `script/debug_judge.py` gọi thẳng `build_llm(...).with_structured_output(...)` không có `try/except` để traceback lộ ra thay vì bị `metrics.py` nuốt. Lần lượt xử lý 3 lỗi xuất hiện tuần tự: model Gemini bị deprecate (đổi model) → quota Gemini free tier hết (đổi provider sang DeepSeek qua nhánh `custom` có sẵn trong `llm.py`) → DeepSeek từ chối `response_format=json_schema` (đổi `method="function_calling"`) → DeepSeek từ chối ép `tool_choice` khi đang ở thinking mode (tắt thinking mode qua `extra_body`).

Với việc merge: dùng nguyên tắc "file thuộc nhiệm vụ của ai thì giữ code của người đó" khi có conflict — kiểm tra bằng `git merge-tree` (dry-run, không chạm working tree) trước khi merge thật, để biết trước file nào bị "changed in both" và liệu code của nhánh kia có thực sự phụ thuộc vào file bị giữ nguyên hay không (ví dụ xác nhận `corruption_flow.py` của Thắng không import `quality.py`/`reporting.py`/`testset.py`, nên giữ bản của Tín cho 3 file này an toàn).

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Cleaned dataframe (`data/clean/papers_clean.json`, do Quân tạo), câu hỏi từ `testset.py` (do Tín tạo) |
| Output                         | `data/results/baseline_metrics.json`, `baseline_answers.json` với judge thật; nhánh `NguyenXuanHung` đã merge đủ code 4 người |
| Module phụ thuộc             | `retrieval/index.py`, `retrieval/embeddings.py` (không sửa, chỉ đọc hiểu) |
| Module sử dụng output        | `pipelines/phase1.py` (Tín), `pipelines/corruption_flow.py` (Thắng) — cả hai đều gọi `answer_question()`/`evaluate_pipeline()` mà tôi đã sửa |
| Điều kiện lỗi cần xử lý | LLM provider hết quota/deprecate (404), structured-output không tương thích giữa các provider, git lock file khi merge |

### Cách xác minh

```bash
uv run python script/debug_judge.py
uv run python script/run_phase1.py
grep -c "Fallback heuristic" data/results/baseline_answers.json
```

- **Kết quả mong đợi:** `debug_judge.py` in ra `JudgeVerdict(...)` không traceback; `grep` trả về `0`.
- **Kết quả thực tế:** Đúng như mong đợi sau vòng sửa lỗi thứ 3 (model → quota → response_format → thinking mode).
- **Artifact/log:** `data/results/baseline_metrics.json`, `data/results/baseline_answers.json` (đã kiểm tra không chứa API key).

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần chọn LLM provider cho judge sau khi `gemini-2.5-flash` bị deprecate và `gemini-3.5-flash` (thay thế trực tiếp) hết quota free tier (RPM 5/5, RPD gần chạm hạn mức).
- **Các phương án đã cân nhắc:** (1) Tiếp tục dùng Gemini, chờ reset quota hoặc nâng cấp trả phí; (2) Chuyển sang DeepSeek qua nhánh `custom` (OpenAI-compatible) đã có sẵn trong `llm.py`, dùng key DeepSeek riêng của tôi.
- **Phương án đã chọn:** Chuyển sang DeepSeek (`deepseek-v4-flash`).
- **Lý do:** Không cần sửa `build_llm()` nhiều (chỉ thêm cấu hình tắt thinking mode), không phụ thuộc quota Gemini free tier đang cạn, chi phí thấp (`$0.14`/1M input token cache-miss), đủ hỗ trợ Tool Calls và JSON Output cần cho structured judge.
- **Bằng chứng quyết định phù hợp:** Sau khi chuyển, `judge_accuracy` và `mean_judge_score` phản ánh đánh giá thật (reasoning là câu văn LLM sinh ra, không còn "Fallback heuristic"), pipeline chạy hết 24 câu ổn định không bị rate-limit.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `openai.BadRequestError: Error code: 400 - {'error': {'message': 'Thinking mode does not support this tool_choice', ...}}`
- **Lệnh hoặc bước tái hiện:** `uv run python script/debug_judge.py` sau khi đã đổi `LLM_PROVIDER=custom` sang DeepSeek và set `method="function_calling"` cho `with_structured_output`.
- **Nguyên nhân gốc:** DeepSeek model `deepseek-v4-flash` mặc định bật "thinking mode" (chain-of-thought trước khi trả lời); ở chế độ này API không cho phép ép `tool_choice` về một hàm cụ thể — điều mà `with_structured_output(method="function_calling")` bắt buộc phải làm để đảm bảo output đúng schema.
- **Cách xử lý:** Thêm `extra_body={"thinking": {"type": "disabled"}}` vào `ChatOpenAI` trong nhánh `custom` của `src/retrieval/llm.py`, theo đúng tham số chính thức DeepSeek công bố trong docs Thinking Mode.
- **Cách xác minh sau khi sửa:** Chạy lại `debug_judge.py` ra `JudgeVerdict(score=..., correct=..., reasoning=...)` thành công; chạy `run_phase1.py` rồi `grep -c "Fallback heuristic"` trả về `0`.
- **Điều học được:** Không nên tin ngay số liệu "đẹp" (`judge_accuracy=1.0`) khi chưa kiểm tra `reasoning`/log chi tiết — số liệu trùng khớp có thể là do nhánh `except Exception` fallback im lặng chứ không phải hệ thống hoạt động đúng.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. Dữ liệu đi từ Crossref (`crossref.py` của Quân, gọi `api.crossref.org/works` với retry cho 429/503) → lưu raw JSON vào `data/raw/` → `cleaning.py` chuẩn hóa thành dataframe với cột `text_for_embedding`, `age_days` → `retrieval/index.py` encode `text_for_embedding` bằng MiniLM và nạp vào ChromaDB (`data/embeddings/`, `data/chroma/`) làm vector index.
2. `testset.py` (Tín) sinh câu hỏi trực tiếp từ từng dòng dataframe clean, nên `ground_truth` và `ground_truth_doc_ids` luôn khớp chính xác với `paper_id` của dòng đó — nhờ vậy `evaluate_pipeline()` trong `metrics.py` có thể so sánh `retrieved_doc_ids` (từ `index.search()`) với `ground_truth_doc_ids` để tính `retrieval_hit_rate`, và so `answer` (từ `qa.py`) với `ground_truth` để tính `token_f1`/judge score.
3. Quality checks (`run_data_quality_checks`) đo tại một thời điểm — hợp lệ/không hợp lệ theo cấu trúc dữ liệu hiện tại (null, trùng lặp, độ dài). Freshness monitoring (`build_freshness_report`) đo theo thời gian — dữ liệu có "cũ" so với ngưỡng `freshness_threshold_days` hay không. Một record có thể pass toàn bộ quality check nhưng vẫn bị đánh dấu stale, hoặc ngược lại.
4. Phải dùng cùng test set cho cả 3 trạng thái vì nếu sinh lại câu hỏi trên dữ liệu corrupted, `ground_truth` sẽ tự "thích nghi" theo lỗi (ví dụ sinh câu hỏi từ summary rỗng), khiến metric không còn đo được tác động thật của corruption — mất khả năng so sánh baseline/corrupted/repaired trên cùng một "đề thi".
5. Repair được coi là thành công khi cả hai lớp bằng chứng khớp: (a) `data/quality/repaired_quality.json` pass 7/7 check với `details` toàn 0 (giống hệt baseline), và (b) 4 metric agent (`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score`) trong `repaired_metrics.json` quay về đúng giá trị `baseline_metrics.json` — không chỉ "tốt hơn corrupted" mà phải bằng baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      1.0 |     0.625 |      1.0 | Giảm 37.5% — noise + truncate title đủ mạnh để đẩy tài liệu đúng ra khỏi top-4 |
| `mean_token_f1`      |      1.0 |    0.5028 |      1.0 | Giảm gần một nửa vì trả lời rỗng/lệch khi summary bị corrupt |
| `judge_accuracy`     |      1.0 |       0.5 |      1.0 | DeepSeek nhận diện đúng câu trả lời sai, không "dễ dãi" cho điểm |
| `mean_judge_score`   |      1.0 |    3.0833 |      1.0 | (thang 1–5) Giảm gần 2 điểm, tương ứng mức giảm token_f1 |
| Quality checks         |    Pass |      Fail |     Pass | 4/7 check fail đúng như 6 kịch bản corruption thiết kế |
| Freshness status       |    Fresh |     Stale |    Fresh | Đúng 3 record bị `make_published_date_stale` |

### Kết luận từ số liệu

1. `blank_summary` + `inject_text_noise` (6 record) → `text_for_embedding` bị rỗng/nhiễu → `retrieval_hit_rate` giảm còn 0.625 và `mean_token_f1` giảm còn 0.503.
2. Repair từ `data/raw/` (nguồn chưa từng bị corruption chạm tới) → `repaired_quality.json` pass 7/7, `is_fresh: true` → cả 4 metric agent phục hồi về đúng 1.0/1.0/1.0/5, chứng minh repair là khôi phục thật từ nguồn tin cậy, không phải sửa tạm trên dữ liệu lỗi.

Corruption ảnh hưởng rõ nhất: `blank_summary` và `inject_text_noise`, vì cả hai cùng phá hỏng `text_for_embedding` — nguồn duy nhất nuôi cả retrieval (semantic search) lẫn answer extraction (`first_sentence(summary)`), nên tác động lan sang cả 4 metric cùng lúc thay vì chỉ 1 chỉ số.

Kết quả khác kỳ vọng ban đầu: lần chạy đầu tiên `judge_accuracy = 0.667` và `mean_judge_score = 3.67` "nhìn hợp lý" nhưng thực chất là do 24/24 câu rơi vào nhánh fallback heuristic (che bởi `except Exception`), không phải LLM chấm thật. Tôi đã kiểm tra bằng cách grep `"Fallback heuristic"` trong `baseline_answers.json` thay vì chỉ tin vào số liệu tổng hợp.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Một pipeline data — dù raw/clean/embedding đều đúng — vẫn có thể cho ra metric sai nếu một khâu trung gian (ở đây là keyword-matching trong `qa.py`) không đồng bộ với cách khâu khác (ở đây là cách đặt câu hỏi trong `testset.py`) tạo ra dữ liệu.
2. Data quality checks và metric của agent là hai lớp bằng chứng bổ sung cho nhau: quality check cho biết *dữ liệu* có vấn đề gì, còn metric agent cho biết vấn đề đó *ảnh hưởng thế nào* đến người dùng cuối — cần cả hai để kết luận đầy đủ.
3. Số liệu "đẹp" không tự động đồng nghĩa hệ thống đúng — luôn cần đọc log/reasoning chi tiết (không chỉ số tổng hợp) trước khi kết luận, đặc biệt khi code có nhánh `except Exception` có thể âm thầm che lỗi.

### Nếu có thêm thời gian

Sẽ bổ sung log tường minh (thay vì fallback im lặng) mỗi khi `_judge_answer()` rơi vào nhánh `except`, ghi rõ loại lỗi (quota/format/khác) ra một file riêng (`data/results/judge_errors.log`). Cách đo cải thiện: số lần fallback trong log phải luôn bằng 0 ở một lần chạy "sạch", nếu khác 0 thì phải có lý do rõ ràng đi kèm thay vì chỉ số bị pha loãng bởi heuristic.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Xuân Hùng
**Ngày xác nhận:** 2026-08-06
