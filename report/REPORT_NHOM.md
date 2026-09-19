# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** Nhóm 4 (AI VinUni)
**Thành viên:** 
1. Ngô Gia Quốc - 02757(HeadingChunker)
2. Nguyễn Hải Đăng - 02963 (FixedSizeChunker)
3. Nguyễn Thị Mừng - 02575 (RecursiveChunker)
4. Bùi Thị Ngọc Trân - 2A202602529 (SentenceChunker)
**Ngày:** 19/09/2026

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Các chính sách, quy định và dịch vụ học vụ tại VinUni.

**Tại sao nhóm chọn chủ đề này?**
> *Viết 2-3 câu:* Bộ dữ liệu này có ý nghĩa thực tiễn cao, giúp sinh viên tra cứu nhanh các quy định học vụ phức tạp. Ngoài ra, văn bản có cấu trúc phân cấp (Heading) rõ ràng và đa dạng thể loại, rất lý tưởng để nhóm so sánh trực tiếp sức mạnh của 4 thuật toán Chunking khác nhau.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | Thời khóa biểu & Đăng ký học phần | dang-ky-hoc-phan.md | 2026-09-19 / v1.0 | 5460 | `audience`, `source_url`, `retrieved_at`, `document_version`, `department` |
| 2 | Chuyển đổi tín chỉ | chuyen-doi-tin-chi.md | 2026-09-19 / v1.0 | 4587 | `audience`, `source_url`, `retrieved_at`, `document_version`, `department` |
| 3 | Yêu cầu cấp Bảng điểm | cap-bang-diem.md | 2026-09-19 / v1.0 | 7028 | `audience`, `source_url`, `retrieved_at`, `document_version`, `department` |
| 4 | Chính sách & Quy định Học thuật | chinh-sach-quy-dinh.md | 2026-09-19 / v1.0 | 7490 | `audience`, `source_url`, `retrieved_at`, `document_version`, `department` |
| 5 | Kỳ thi và điểm | ky-thi-diem.md | 2026-09-19 / v1.0 | 2949 | `audience`, `source_url`, `retrieved_at`, `document_version`, `department` |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `audience` | string | `student`, `faculty` | Cho phép lọc nhanh tài liệu theo đối tượng người dùng. |
| `source_url` | string | `https://...` | Truy xuất nguồn gốc và kiểm chứng thông tin. |
| `retrieved_at` | string | `2023-10-01` | Theo dõi phiên bản và thời gian thu thập dữ liệu. |
| `document_version`| string | `v1.0` | Đảm bảo sử dụng tài liệu phiên bản mới nhất. |
| `department` | string | `Registrar` | Khoanh vùng đơn vị ban hành quy định. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

Mỗi thành viên trong nhóm đảm nhận một chiến lược Chunking & Metadata.

| Vai trò | Tên thành viên | Cấu trúc Metadata (Các trường được dùng) | Cấu hình Chunking (Tham số) |
|---|---|---|---|
| Heading Chunker | Ngô Gia Quốc | `audience`, `source_url`, `retrieved_at`, `document_version`, `department` | `chunk_size=500` |
| Fixed Size Chunker | Nguyễn Hải Đăng - 02963 | `audience`, `source_url`, `retrieved_at`, `document_version`, `department` | `chunk_size=500`, `overlap=50` |
| Recursive Chunker | Nguyễn Thị Mừng - 02575 | `audience`, `source_url`, `retrieved_at`, `document_version`, `department` | `chunk_size=500`, `separators` mặc định |
| Sentence Chunker | Bùi Thị Ngọc Trân - 2A202602529 | `audience`, `source_url`, `retrieved_at`, `document_version`, `department` | `max_sentences_per_chunk=3` |

> *Lưu ý (L3A): Tất cả các thành viên đều phải dùng metadata `audience` (student/faculty/staff/all) và ít nhất 1 trường bổ sung. Thành viên làm Recursive Chunker đã sử dụng Markdown headers làm `separators`.*

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` trên 2-3 tài liệu:

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| Đăng ký học phần | FixedSizeChunker (`fixed_size`) | 9 | 470 ký tự | Khá |
| Đăng ký học phần | SentenceChunker (`by_sentences`) | 16 | 237 ký tự | Nhỏ quá, dễ mất ngữ cảnh lớn |
| Đăng ký học phần | RecursiveChunker (`recursive`) | 8 | 476 ký tự | Rất tốt |

### Chiến lược của từng thành viên

**Thành viên 1 — Ngô Gia Quốc**
- **Loại chiến lược:** HeadingChunker
- **Mô tả & lý do chọn cho chủ đề này:** Tách văn bản dựa trên các đề mục (headings). Thích hợp cho tài liệu được cấu trúc chặt chẽ bằng markdown, giúp mỗi chunk chứa trọn vẹn một ý chính.
- **Code snippet:**
```python
CHUNKER = HeadingChunker(chunk_size=500)
```

**Thành viên 2 — Nguyễn Hải Đăng**
- **Loại chiến lược:** FixedSizeChunker
- **Mô tả & lý do chọn:** Chia văn bản thành các khối có độ dài ký tự cố định kèm theo khoảng gối (overlap). Dễ cài đặt, phù hợp cho văn bản liền mạch không có cấu trúc đoạn rõ ràng.
- **Code snippet:**
```python
CHUNKER = FixedSizeChunker(chunk_size=500, overlap=50)
```

**Thành viên 3 — Nguyễn Thị Mừng**
- **Loại chiến lược:** RecursiveChunker
- **Mô tả & lý do chọn:** Chia nhỏ văn bản đệ quy qua danh sách các dấu phân cách (từ `#` đến `\n` và khoảng trắng). Giúp ưu tiên giữ lại các cụm ý nghĩa trọn vẹn theo ngữ pháp và cấu trúc.
- **Code snippet:**
```python
markdown_separators = ["\n# ", "\n## ", "\n### ", "\n\n", "\n", ". ", " "]
CHUNKER = RecursiveChunker(separators=markdown_separators, chunk_size=500)
```

**Thành viên 4 — Bùi Thị Ngọc Trân**
- **Loại chiến lược:** SentenceChunker
- **Mô tả & lý do chọn:** Chia nhỏ văn bản theo câu. Hữu ích cho các văn bản pháp lý hoặc quy định nơi mỗi câu chứa một điều khoản cụ thể, tránh việc trộn lẫn ý giữa các câu.
- **Code snippet:**
```python
CHUNKER = SentenceChunker(max_sentences_per_chunk=3)
```

### So Sánh Giữa Các Thành Viên

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Ngô Gia Quốc | Heading | 9.0 | Giữ ngữ cảnh tốt cho tài liệu cấu trúc mạnh | Gặp lỗi nếu văn bản không có heading |
| Nguyễn Hải Đăng | FixedSize | 7.0 | Đơn giản, đảm bảo đúng kích thước | Dễ cắt đứt câu, hỏng ngữ cảnh |
| Nguyễn Thị Mừng | Recursive | 9.5 | Cân bằng hoàn hảo giữa kích thước và ngữ nghĩa | Cấu hình separator phức tạp |
| Bùi Thị Ngọc Trân | Sentence | 7.5 | Bắt đúng tiểu tiết nhỏ (số liệu) | Bị nhiễu, mất ngữ cảnh tổng thể |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> *Viết 2-3 câu — đây là phần được đánh giá cao nhất (khả năng suy nghĩ & giải thích):*
> Chiến lược Recursive Chunker là tốt nhất vì tài liệu quy định đại học có cấu trúc phân cấp rõ ràng (chương, điều, mục). Việc dùng Markdown headers làm separators giúp giữ nguyên vẹn ngữ cảnh của từng điều luật thay vì cắt cụt ngẫu nhiên.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | Tối đa bao nhiêu tín chỉ được phép chuyển vào chương trình đại học tại VinUni? | Tối đa 60 tín chỉ. | Tra cứu tài liệu chuyển đổi tín chỉ. |
| 2 | Học phần cần đáp ứng mức tương đương nội dung và điểm tối thiểu nào để được xem xét chuyển đổi tín chỉ? | Nội dung tương đương ít nhất 70% và điểm tối thiểu là C hoặc tương đương. | Tra cứu tài liệu chuyển đổi tín chỉ. |
| 3 | Trên SIS cần thao tác thế nào để hoàn tất đăng ký môn và trạng thái nào xác nhận đăng ký thành công? | Nhấn “Add”, sau đó “Register”; trạng thái phải là “Registered”. | Tra cứu tài liệu đăng ký học phần. |
| 4 | Yêu cầu bảng điểm hoặc thư xác nhận thường mất bao lâu và phí mỗi bản là bao nhiêu? | Thông thường 2–3 ngày làm việc, có thể đến 5 ngày vào mùa cao điểm; phí 50.000 VNĐ mỗi bản. | Tra cứu tài liệu cấp bảng điểm. |
| 5 | Cần thực hiện những bước nào để đăng ký học phần? | Đăng nhập SIS, mở Course Registration, tìm môn, nhấn Add rồi Register và kiểm tra Your Class Schedule. | Bắt buộc áp dụng bộ lọc `metadata_filter={"audience": "student"}` |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | Tối đa bao nhiêu tín chỉ được phép chuyển... | Đều tốt (Heading/Fixed/Recursive/Sentence) | Có (Top 1 cho tất cả) | Cả 4 thuật toán đều đẩy chunk chứa đáp án lên top 1. |
| 2 | Học phần cần đáp ứng mức tương đương nội dung... | Heading / Fixed / Recursive | Có (Top 1) | SentenceChunker cắt quá nhỏ nên mất đi ngữ cảnh, không lọt top 3. |
| 3 | Trên SIS cần thao tác thế nào để hoàn tất... | HeadingChunker | Có (Top 1 cho Heading, Top 3 cho Recursive) | HeadingChunker gom đoạn tốt nhất. FixedSize cắt ngang câu khiến mất ý nghĩa. |
| 4 | Yêu cầu bảng điểm hoặc thư xác nhận thường mất... | SentenceChunker | Có (Top 3 cho Sentence) | Các thuật toán lớn bị nhiễu nội dung, SentenceChunker lấy chi tiết chính xác hơn. |
| 5 | Cần thực hiện những bước nào để đăng ký học phần? | Không có thuật toán nào nổi bật | Có (Top 1 tìm được đúng tài liệu nhưng khác đoạn văn) | Dù không chứa nguyên đoạn marker, nhưng đã đẩy đúng tài liệu hướng dẫn lên vị trí Top 1. |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> *Viết 2-3 câu:* Rất hữu ích. Ở câu hỏi số 5 (đăng ký học phần), nếu áp dụng filter `{"audience": "student"}`, kết quả sẽ ngay lập tức loại bỏ các tài liệu không liên quan đến sinh viên, giúp tài liệu đăng ký môn học vững chắc ở Top 1 với độ tự tin (score) cực cao. Nếu không có filter, hệ thống sẽ phải so sánh với toàn bộ các chính sách nội bộ khác gây tốn kém thời gian và dễ nhầm lẫn.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> *Liệt kê 2-3 ý:* 
> - Cấu trúc thẻ Heading (##) cực kỳ hữu ích cho tài liệu luật/quy định.
> - Metadata `audience` giúp cô lập nhanh vùng dữ liệu.
> - Retrieval vẫn có thể tìm nhầm nếu từ khóa chung chung.

**Bài học rút ra khi so sánh trong nhóm:**
> *Viết 2-3 câu:* Cùng một tài liệu, Recursive chunking duy trì độ chính xác và tính toàn vẹn (coherence) tốt hơn nhiều so với FixedSize. Metadata filter là tính năng bắt buộc khi quy mô dữ liệu lớn để tránh nhiễu.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> *Viết 2-3 câu:* Nhóm sẽ cố gắng thiết kế cấu trúc Markdown của văn bản đầu vào chuẩn hơn trước khi đưa vào chunker, và sử dụng LLM để sinh ra tóm tắt (summary) cho từng chunk làm metadata bổ sung, giúp retrieval chính xác hơn.


---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 10 / 10 |
| Thiết kế chiến lược (Strategy Design) | 15 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 10 / 10 |
| Thuyết trình (Demo) | 5 / 5 |
| **Tổng phần nhóm** | **40 / 40** |
