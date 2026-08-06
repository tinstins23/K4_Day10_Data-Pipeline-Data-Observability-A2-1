# Phân công công việc - Data Pipeline & Observability

## Thành viên 1: Hoàng Minh Quân — Data Engineer (Thu thập & Làm sạch dữ liệu)

**Nhiệm vụ:**

- Implement logic gọi API Crossref (`api.crossref.org/works`), xử lý rate-limit (429/503) bằng retry/backoff.
- Lưu raw response vào `data/raw/` để đảm bảo tính truy vết.
- Viết code làm sạch trong `cleaning.py`: loại bỏ bản ghi lỗi, chuẩn hóa title/summary/authors, tạo cột text cho embedding và tính `age_days`.

**Mốc hoàn thành:** Xong đầu tiên để cung cấp dữ liệu sạch cho cả nhóm.

---

## Thành viên 2: Nguyễn Xuân Hùng — RAG & Evaluation Engineer (Đánh giá & Kiểm thử Agent)

**Nhiệm vụ:**

- Đọc và hiểu logic vectorization trong `src/retrieval/` (sử dụng mô hình MiniLM và ChromaDB).
- Hoàn thành `src/evaluation/testset.py`: Tự động tạo tập câu hỏi evaluation (đảm bảo đủ trường `question`, `ground_truth`, `ground_truth_doc_ids`, `question_type`).
- Phối hợp chạy thử Agent (`src/retrieval/agent.py`) để xác nhận hệ thống tính toán đúng các metric: `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score`.

---

## Thành viên 3: Hồ Trung Tín — Observability Engineer (Giám sát chất lượng & Điều phối Pha 1)

**Nhiệm vụ:**

- Implement các bộ kiểm tra chất lượng (Data Quality Checks) và giám sát độ tươi (Freshness Monitoring) trong `src/observability/quality.py`.
- Hoàn thành `src/observability/reporting.py` để xuất báo cáo Markdown.
- Ghép nối toàn bộ luồng Pha 1 trong `src/pipelines/phase1.py`. Đảm bảo khi chạy lệnh `uv run python script/run_phase1.py` hệ thống tự động sinh đủ các artifacts cho baseline.

---

## Thành viên 4: Thắng — Chaos & Reliability Engineer (Kiểm thử lỗi, Phục hồi & Điều phối Pha 2)

**Nhiệm vụ:**

- Viết các hàm gây lỗi dữ liệu trong `src/ingestion/corruption.py` theo đủ 6 kịch bản: xóa record mới, blank summary, thêm noise, truncate title, làm cũ date, và tạo duplicate.
- Viết cơ chế repair: Đọc lại từ `data/raw/` để làm sạch và khôi phục dữ liệu về trạng thái ban đầu.
- Ghép nối luồng Pha 2 trong `src/pipelines/corruption_flow.py` và chạy script `run_corruption_flow.py`.
- Chịu trách nhiệm tổng hợp số liệu của cả 3 trạng thái (Baseline - Corrupted - Repaired) để hoàn thiện báo cáo cuối cùng (`corruption_report.md`).

---

## Lưu ý phối hợp

- Thứ tự phụ thuộc: Thành viên 1 hoàn thành trước để cung cấp dữ liệu sạch cho Thành viên 2 và 3.
- Thành viên 4 cần dữ liệu baseline từ Thành viên 3 (Pha 1) trước khi chạy Pha 2 (corruption flow).
- Thành viên 2 và 3 có thể làm song song sau khi có dữ liệu sạch từ Thành viên 1.
