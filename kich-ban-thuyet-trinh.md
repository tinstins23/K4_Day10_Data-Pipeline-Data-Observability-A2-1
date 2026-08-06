# Kịch bản thuyết trình — Data Pipeline & Data Observability (Nhóm A2-1)

> Tổng thời lượng gợi ý: 6–8 phút. Mở song song file `demo_dashboard.html` để trình chiếu trực tiếp theo từng phần.

## 1. Mở đầu (30 giây)

"Nhóm em xây một pipeline RAG (Retrieval-Augmented Generation) trên dữ liệu bài báo khoa học lấy từ Crossref. Trọng tâm không chỉ là làm cho hệ thống chạy được, mà là **chứng minh chất lượng dữ liệu ảnh hưởng trực tiếp đến chất lượng câu trả lời của AI** — và khi dữ liệu bị lỗi, hệ thống có phát hiện và tự phục hồi được không."

*(Mở `demo_dashboard.html`, để ở mục 1 — sơ đồ luồng.)*

## 2. Kiến trúc pipeline (1 phút)

Chỉ vào sơ đồ luồng, đọc theo đúng thứ tự mũi tên:

"Dữ liệu đi qua 9 bước: lấy từ **Crossref API** → lưu **raw** để truy vết → **làm sạch** (chuẩn hóa tên tác giả, tính độ mới `age_days`) → tạo **embedding** bằng MiniLM và nạp vào **ChromaDB** → sinh **24 câu hỏi đánh giá** → chấm điểm agent → kiểm tra **chất lượng & độ tươi dữ liệu** → **cố tình làm hỏng dữ liệu** theo 6 kịch bản → **sửa lại** từ nguồn gốc → **so sánh** 3 trạng thái."

Điểm nhấn: "Baseline, corrupted và repaired đều dùng **chung một bộ 24 câu hỏi** — để phép so sánh công bằng, không phải so sánh 2 đề thi khác nhau."

## 3. Demo chatbot (2 phút) — phần trực quan nhất

*(Chuyển sang mục 2 — Demo Chatbot.)*

"Đây là agent thật, tụi em cho gõ trực tiếp." Gõ hoặc bấm 1–2 chip gợi ý, ví dụ:

- "SafeRAG nói về gì?" → bot trả lời tóm tắt
- "Ai là tác giả của JADE-Plus?" → bot trả lời tên tác giả

Bấm vào nút **"📄 Nguồn"** để mở thẳng DOI thật trên trình duyệt:

"Mỗi câu trả lời đều có trích dẫn bấm được — đây là yêu cầu quan trọng của RAG: không trả lời từ trí nhớ mô hình, mà trả lời có bằng chứng, người dùng kiểm tra lại được nguồn gốc."

*(Lưu ý nói rõ: phần chat này chạy offline trong trình duyệt để demo nhanh không tốn token, nhưng logic khớp câu hỏi — trích dẫn mô phỏng đúng những gì agent thật (DeepSeek + ChromaDB) đã trả lời khi chạy pipeline.)*

## 4. Kết quả baseline (1 phút)

*(Chuyển sang mục 3 — biểu đồ metrics, chỉ cột "Baseline".)*

"Trên 24 câu hỏi, agent đạt tuyệt đối: `retrieval_hit_rate = 1.0` (luôn tìm đúng tài liệu), `mean_token_f1 = 1.0`, và LLM giám khảo (DeepSeek) chấm `judge_accuracy = 1.0`, điểm trung bình `5/5`."

## 5. Thử nghiệm corruption — phần "gây bệnh rồi chữa" (2 phút)

*(Chuyển sang mục 5 — 6 kịch bản corruption.)*

"Để chứng minh dữ liệu xấu thực sự gây hại, tụi em cố tình phá 18/24 bản ghi theo 6 cách:" — đọc nhanh 2–3 ví dụ tiêu biểu, không cần đọc hết 6:

- "Xóa 3 bài mới nhất, làm 3 bài khác **rỗng phần tóm tắt**, chèn nhiễu vào 3 bài khác, cắt cụt tiêu đề, làm cũ ngày xuất bản, và nhân bản 3 bài."

*(Chuyển sang mục 3, so 3 cột Baseline/Corrupted/Repaired.)*

"Kết quả: `retrieval_hit_rate` rớt từ 1.0 xuống **0.625**, điểm giám khảo rớt từ 5 xuống **3.08/5**. Data quality check cũng báo fail đúng 4 lỗi: trùng ID, tóm tắt rỗng/ngắn, dữ liệu cũ."

*(Nhấn mạnh:)* "Sau đó tụi em **repair — đọc lại từ dữ liệu raw gốc**, không sửa tay trên bản lỗi. Kết quả phục hồi về **chính xác** bằng baseline: 1.0 / 1.0 / 1.0 / 5 — chứng minh đây là khôi phục thật từ nguồn tin cậy, không phải che giấu lỗi."

## 6. Kết luận (30 giây)

"Ba điều tụi em rút ra: (1) một lỗi nhỏ ở tầng dữ liệu (tóm tắt rỗng, nhiễu văn bản) có thể kéo giảm cả retrieval lẫn câu trả lời cuối cùng của AI; (2) data quality check và metric của agent là hai lớp bằng chứng cần dùng cùng nhau; (3) repair phải xác minh bằng số liệu quay về đúng baseline, không chỉ 'nhìn có vẻ tốt hơn'."

"Cảm ơn thầy/cô và các bạn đã lắng nghe, tụi em sẵn sàng trả lời câu hỏi."

---

## Câu hỏi thường gặp — chuẩn bị trước câu trả lời

| Câu hỏi có thể gặp | Trả lời gợi ý |
| --- | --- |
| Tại sao chỉ có 24 câu hỏi, có ít quá không? | Giới hạn bởi `max_results=24` khi gọi Crossref để pipeline chạy nhanh lúc demo; kiến trúc hỗ trợ scale lên vài trăm record không đổi code. |
| Vì sao không có câu hỏi loại "categories"? | Trường `categories` từ Crossref phần lớn rỗng với query hiện tại, hệ thống tự động bỏ qua câu hỏi không có ground truth hợp lệ thay vì tạo câu hỏi sai. |
| Chatbot trong demo có phải AI thật không? | Phần chat trên slide là mô phỏng offline (khớp từ khóa) dựng lại đúng nội dung agent thật (DeepSeek + ChromaDB) đã trả lời khi chạy `run_phase1.py` — dùng để demo nhanh không phụ thuộc mạng/API. |
| Làm sao biết repair là "thật" chứ không phải chỉnh số liệu? | Repair đọc lại từ `data/raw/` (dữ liệu gốc chưa từng bị corruption chạm tới) và chạy lại đúng hàm cleaning ban đầu — có thể mở `corruption_flow.py` cho xem code, không có bước nào ghi đè trực tiếp lên metric. |
| Dùng LLM nào để chấm điểm? | DeepSeek (`deepseek-v4-flash`) qua endpoint tương thích OpenAI, chọn vì miễn phí/rẻ hơn và không giới hạn quota chặt như Gemini free tier lúc nhóm demo. |
