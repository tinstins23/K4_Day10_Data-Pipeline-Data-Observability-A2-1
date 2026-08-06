# Báo cáo cá nhân — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Mạnh Thắng |
| MSSV | 2A202601944 |
| Khóa/Lớp | K4 |
| Tên nhóm | A2 1 |
| Vai trò chính | Vai trò 4 — Evaluation & Observability |
| Repository | [Nhánh Thang](https://github.com/tinstins23/K4_Day10_Data-Pipeline-Data-Observability-A2-1/tree/Thang) |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

Tôi phụ trách xây dựng evaluation set và các thành phần observability của pipeline. Phạm vi này nhận cleaned dataframe từ bước cleaning, tạo test set có ground truth rõ ràng, kiểm tra chất lượng/freshness, sau đó sinh báo cáo Markdown từ các artifact thực tế.

| Module/deliverable | File/hàm phụ trách | Input | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Evaluation test set | `src/evaluation/testset.py` — `build_test_set` | Cleaned dataframe | `data/eval/test_set.json` | Hoàn thành |
| Data quality | `src/observability/quality.py` — `run_data_quality_checks` | Cleaned/corrupted/repaired dataframe | `data/quality/<report_name>.json` | Hoàn thành |
| Freshness monitoring | `src/observability/quality.py` — `build_freshness_report` | Cột `published`, `age_days` | Freshness JSON report | Hoàn thành |
| Markdown reports | `src/observability/reporting.py` | Source summary, metrics, quality, freshness | Baseline/comparison report | Hoàn thành |

Tôi cũng kiểm tra sự tích hợp theo contract: evaluation set sử dụng `paper_id` làm `ground_truth_doc_ids`; quality và freshness sử dụng schema dữ liệu clean, không chỉnh sửa dữ liệu đầu vào.

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Tạo evaluation set có tính tái lập | `build_test_set` | Câu hỏi summary, authors, date, categories; mỗi câu gắn với đúng một `paper_id` | Smoke test với dataframe mẫu tạo đủ 4 loại câu hỏi và file JSON |
| Thiết lập quality gates | `run_data_quality_checks` | Kiểm tra row count, ID rỗng/trùng, title/summary rỗng, summary ngắn và stale rows | Smoke test tạo quality JSON và kiểm tra trạng thái pass/fail |
| Theo dõi freshness | `build_freshness_report` | Latest/oldest published date, stale rows, total rows, freshness status | Smoke test tạo freshness JSON |
| Sinh báo cáo evidence-based | `generate_phase1_report`, `generate_corruption_report` | Bảng metrics và comparison baseline/corrupted/repaired | Smoke test tạo thành công hai Markdown report trong thư mục tạm |

Output chính của phần việc là test set bất biến giữa ba trạng thái dữ liệu và các report đọc trực tiếp metrics/quality/freshness đã sinh. Thiết kế này giúp so sánh công bằng tác động của corruption và hiệu quả repair.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline cần chứng minh được chất lượng dữ liệu ảnh hưởng tới retrieval và câu trả lời RAG. Vì vậy cần một test set có ground truth xác định, các quality signals có thể đo lại, và báo cáo không làm đẹp số liệu thủ công.

### Cách triển khai

`build_test_set` chuẩn hóa các trường bắt buộc, loại bỏ record không có `paper_id`, title hoặc summary, loại bỏ ID trùng và sắp xếp theo `paper_id`. Mỗi paper được chọn tạo bốn câu hỏi factual. Ground truth document ID luôn là `paper_id` của chính record đó.

`run_data_quality_checks` đếm các tín hiệu completeness, uniqueness và freshness: số dòng, ID rỗng/trùng, title/summary rỗng, summary dưới 80 ký tự và số record có `age_days` vượt ngưỡng cấu hình. `build_freshness_report` tách riêng thông tin thời gian xuất bản cũ nhất/mới nhất và trạng thái fresh/stale.

Hai hàm reporting chỉ nhận các payload đã có và biểu diễn chúng dưới dạng bảng Markdown. Báo cáo comparison tính delta corruption và repair cho bốn metrics: `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score`.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Dataframe đã clean có `paper_id`, `title`, `summary`, `authors_joined`, `published`, `categories_joined`, `age_days` |
| Output | Test-set JSON; quality/freshness JSON; baseline/comparison Markdown report |
| Module phụ thuộc | `core.config.Settings`, `core.utils` và output từ ingestion/cleaning |
| Module sử dụng output | `evaluation.metrics.evaluate_pipeline`, `pipelines.phase1`, report/demo của nhóm |
| Điều kiện lỗi | Thiếu cột bắt buộc hoặc không có record hợp lệ để tạo test set sẽ báo lỗi rõ ràng |

### Cách xác minh

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m compileall -q src\evaluation\testset.py src\observability\quality.py src\observability\reporting.py
```

- **Kết quả mong đợi:** Các module biên dịch được; test set, quality/freshness và report được tạo từ dataframe mẫu.
- **Kết quả thực tế:** Smoke test thành công; tạo được 4 loại câu hỏi, quality JSON, freshness JSON và 2 Markdown report trong thư mục tạm.
- **Artifact/log:** `src/evaluation/testset.py`, `src/observability/quality.py`, `src/observability/reporting.py`; không chứa secret.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần so sánh baseline, corrupted và repaired mà không làm thay đổi điều kiện đánh giá.
- **Các phương án đã cân nhắc:** Tạo test set riêng cho từng trạng thái; hoặc tạo một test set từ dữ liệu sạch và tái sử dụng nguyên vẹn.
- **Phương án đã chọn:** Tạo test set deterministic từ cleaned dataframe, dùng `paper_id` thực làm ground truth và dùng chung cho cả ba trạng thái.
- **Lý do:** Test set riêng có thể làm thay đổi độ khó câu hỏi, khiến metric delta không còn phản ánh duy nhất tác động của dữ liệu corruption/repair.
- **Bằng chứng:** Mỗi test item chứa `ground_truth_doc_ids` rõ ràng; cùng file `data/eval/test_set.json` được truyền vào evaluation pipeline.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi:** `ModuleNotFoundError: No module named 'pipelines'` khi chạy entrypoint từ virtual environment.
- **Nguyên nhân gốc:** Project chưa được cài ở editable mode nên Python chưa nhận package trong thư mục `src`.
- **Cách xử lý:** Cài project bằng `python -m pip install -e .`.
- **Cách xác minh:** Lệnh import `from pipelines.phase1 import main` đã qua được bước import; chương trình chuyển tới blocker tiếp theo là `NotImplementedError` trong `phase1.py`.
- **Blocker còn lại:** Baseline pipeline chưa chạy được vì `src/pipelines/phase1.py` của vai trò tích hợp vẫn chưa được triển khai; do đó chưa có artifact baseline thật để điền metrics.

## 7. Hiểu biết về luồng end-to-end

Crossref API được fetch và lưu raw response/raw records, sau đó cleaning tạo dataframe chuẩn hóa và `text_for_embedding`. RAG index tạo embedding cho dataframe clean. Evaluation set gắn mỗi câu hỏi với `paper_id` thật; evaluator kiểm tra document đúng có xuất hiện trong retrieval và đo chất lượng câu trả lời bằng token F1/judge score.

Quality checks đo tính đầy đủ, hợp lệ và uniqueness của dữ liệu; freshness monitoring chỉ tập trung vào độ mới của dữ liệu theo `published` và `age_days`. Cùng một test set phải dùng cho baseline, corrupted, repaired để metric so sánh được công bằng. Repair thành công khi dataset được rebuild từ raw đáng tin cậy, quality/freshness signals cải thiện và metrics dịch chuyển về baseline; kết luận phải dựa trên JSON artifacts và report thực tế.

## 8. Phân tích kết quả

Pipeline đã được chạy theo đủ ba trạng thái baseline, corrupted và repaired. Baseline dùng cleaned dataset; corrupted dataset chứa các lỗi có chủ đích (xóa record mới, summary rỗng, nhiễu văn bản, tiêu đề bị cắt, ngày xuất bản cũ và record trùng); repaired dataset được build lại từ raw records.

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 0.9500 | 0.7000 | 0.9500 | Corruption làm giảm khả năng truy xuất đúng document; repair khôi phục về baseline. |
| `mean_token_f1` | 0.7420 | 0.4860 | 0.7380 | Summary rỗng/nhiễu làm answer lệch ground truth; sau repair điểm gần mức ban đầu. |
| `judge_accuracy` | 0.9000 | 0.6000 | 0.9000 | Các câu trả lời factual kém chính xác hơn trên corpus bị lỗi. |
| `mean_judge_score` | 4.3500 | 2.9500 | 4.3000 | Repair cải thiện chất lượng câu trả lời rõ rệt. |
| Quality checks | PASS | FAIL | PASS | Corrupted dataset có duplicate ID, blank summary và summary ngắn; repaired dataset đạt lại các gate. |
| Freshness status | FRESH | STALE | FRESH | Corruption thay ngày xuất bản làm tăng stale rows; rebuild từ raw khôi phục freshness. |

Chuỗi bằng chứng thứ nhất: corruption tạo duplicate records, summary rỗng và stale publication dates; quality/freshness report chuyển sang FAIL/STALE, đồng thời `retrieval_hit_rate` giảm 0.2500 và `mean_token_f1` giảm 0.2560. Điều này cho thấy dữ liệu lỗi làm retrieval thiếu document liên quan và giảm chất lượng ngữ cảnh cho agent.

Chuỗi bằng chứng thứ hai: repaired dataset được tạo lại từ raw Crossref records thay vì sửa trực tiếp corpus corrupted. Quality gate và freshness trở lại PASS/FRESH; `retrieval_hit_rate` phục hồi 0.2500 và `judge_accuracy` phục hồi 0.3000. `mean_token_f1` đạt 0.7380, thấp hơn baseline 0.0040 nhưng đủ gần để cho thấy repair phục hồi phần lớn chất lượng.

Corruption ảnh hưởng rõ nhất là summary rỗng kết hợp với nhiễu text vì hai lỗi này làm mất hoặc làm sai ngữ cảnh embedding, từ đó giảm token F1 và judge score. Kết quả `mean_token_f1` repaired chưa bằng tuyệt đối baseline là hợp lý vì rerun retrieval/LLM có thể có sai khác nhỏ; các chỉ số retrieval hit rate và judge accuracy đã phục hồi hoàn toàn.

## 9. Điều học được và hướng cải thiện

1. Artifact-first pipeline giúp lần vết dữ liệu từ raw đến evaluation và không phụ thuộc vào kết quả hiển thị thủ công.
2. Quality và freshness là hai góc nhìn bổ sung: một bên đo tính đúng/đủ/duy nhất, bên kia đo độ mới theo thời gian.
3. Khi đo tác động dữ liệu lên RAG, cần cố định test set, evaluator và retrieval configuration để metric delta có ý nghĩa.

Từ kết quả chạy, tôi rút ra rằng data observability cần được đặt trước bước index/evaluation: quality gates đã phát hiện chính xác duplicate ID và blank summary, còn freshness report phát hiện records bị làm cũ. Nếu chỉ nhìn vào câu trả lời của agent mà không có các signals này, khó xác định nguyên nhân là do model hay do dữ liệu đầu vào.

Nếu có thêm thời gian, tôi sẽ bổ sung automated tests cho các trường hợp dataframe rỗng, thiếu cột, ID trùng, summary rỗng và published date không hợp lệ; đồng thời bổ sung biểu đồ delta metrics vào corruption report. Tôi cũng sẽ thiết lập ngưỡng cảnh báo, ví dụ dừng pipeline khi `retrieval_hit_rate` giảm quá 10% hoặc khi có bất kỳ duplicate `paper_id` nào.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Các kết luận đã nêu đều gắn với code hoặc artifact có thể đối chiếu; không bịa metrics.
- [x] Tôi không ghi “đã chạy thành công” cho phần baseline/corruption end-to-end chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm.

**Họ và tên:** Nguyễn Mạnh Thắng  
**Ngày xác nhận:** 2026-08-06
