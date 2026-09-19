# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Nguyễn Hải Đăng
**Nhóm:** VSF
**Ngày:** 19/9

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Hai câu/đoạn văn có embedding gần cùng hướng trong không gian vector, tức nội dung ngữ nghĩa gần nhau (cosine tiến về 1). Cosine chỉ quan tâm góc giữa hai vector chứ không quan tâm độ dài, nên "cao" ở đây nghĩa là hai văn bản mang ý nghĩa tương tự.

**Ví dụ có độ tương tự CAO:**
- Câu A: Sinh viên đăng ký học phần qua hệ thống SIS.
- Câu B: Sinh viên đăng ký môn học trên cổng SIS của trường.
- Tại sao tương đồng: Cùng nói về hành động đăng ký môn học qua SIS, chia sẻ gần như toàn bộ từ khóa (sinh viên, đăng ký, học phần/môn học, SIS) → embedding có hướng gần nhau.

**Ví dụ có độ tương tự THẤP:**
- Câu A: Phí cấp bảng điểm là 50.000 VNĐ mỗi bản.
- Câu B: Học phí học kỳ này đã được thanh toán đầy đủ.
- Tại sao khác: Hai phạm trù khác nhau (phí dịch vụ cấp giấy tờ vs học phí kỳ học) và gần như không chia sẻ từ khóa → hướng vector lệch nhau.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Embedding thường được chuẩn hóa theo độ dài và vector dài hay ngắn phụ thuộc tần suất từ xuất hiện. Cosin chỉ đo góc nên bất biến với độ dài (scale-invariant); còn khoảng cách Euclid bị độ dài vector làm sai lệch — hai câu giống ý nhưng độ dài khác nhau vẫn có thể cách xa nhau. Hầu hết embedding model cũng chuẩn hóa vector đơn vị, khi đó cosine và dot product tương đương nhau và rẻ để tính.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> - Bước nhảy (step) = chunk_size − overlap = 500 − 50 = **450**
> - Số chunk = ⌈(10.000 − 500) / 450⌉ + 1 = ⌈21,11⌉ + 1 = 22 + 1 = **23 chunks**
> - Kiểm chứng bằng `FixedSizeChunker(chunk_size=500, overlap=50)` trên chuỗi 10.000 ký tự: cho đúng 23 chunks (chunk cuối dài 100 ký tự).

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Overlap 100 → step = 400 → số chunk = ⌈9500/400⌉ + 1 = 24 + 1 = **25 chunks** (nhiều hơn 23). Overlap nhiều hơn giúp các chunk liên tiếp chia sẻ nhiều ký tự hơn, giảm nguy cơ cắt đứt một ý/đoạn đang dang dở ở biên giới chunk — quan trọng khi câu trả lời nằm trải dài qua biên giới hai chunk.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Dùng regex với lookbehind `(?<=[.!?]) +` để tách câu ngay sau dấu `.`, `!`, `?` khi theo sau là khoảng trắng — một biểu thức bao phủ đủ 4 pattern theo spec (`. `, `! `, `? `, `.\n`). Mỗi câu được `strip()`; các câu rỗng bị bỏ qua (edge case: khoảng trắng liên tiếp, dòng trống). Gom câu vào chunk hiện tại cho tới khi đủ `max_sentences_per_chunk` rồi mở chunk mới; phần dư cuối cùng (chunk chưa đủ số câu tối đa) vẫn được trả về.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> `chunk()` ủy quyền toàn bộ cho `_split(text, separators)`. `_split` có 2 base case: (1) nếu văn bản đã ≤ `chunk_size` thì giữ nguyên — đây là điểm quan trọng tôi sửa trong quá trình chạy benchmark, vì bản đầu không kiểm tra kích thước nên đệ quy xuống tận từng từ; (2) nếu hết separator thì cắt theo ký tự (`sep == ""`). Ngược lại thử separator ưu tiên cao nhất; nếu separator không xuất hiện thì chuyển sang separator kế tiếp; nếu xuất hiện thì đệ quy từng phần với danh sách separator còn lại và gộp kết quả.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> `add_documents` gọi `_make_record`: embedding nội dung bằng `embedding_fn` rồi lưu dict chuẩn gồm `id`, `content`, `embedding`, `metadata`, `doc_id` (lấy từ `doc.id`). Với chế độ in-memory, `search` embedding câu query rồi tính cosine similarity (dot product chia tích chuẩn của hai vector, có chặn 0.0 khi vector zero-magnitude), sắp xếp giảm dần và trả về top-k kèm khóa `score`. Với ChromaDB, dùng `collection.query(query_texts, n_results)`.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> `search_with_filter` lọc **trước** (pre-filter) bằng dict comprehension kiểm tra `r["metadata"].get(key) == value` cho mọi cặp trong `metadata_filter`, sau đó chạy similarity search chỉ trên tập đã lọc — thu hẹp không gian tìm kiếm, tăng precision khi metadata phân biệt nhóm tài liệu (ví dụ `audience`). `delete_document` dùng list comprehension giữ lại các record có `id != doc_id`, rồi so độ dài trước/sau để quyết định trả về `True`/`False`.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Gọi `store.search(question, top_k)` để lấy các chunk liên quan nhất, nối `content` của chúng bằng `"\n\n"` thành khối ngữ cảnh rồi dựng prompt RAG ba phần: `Câu hỏi: …` / `Ngữ cảnh: …` / `Câu trả lời:`. Toàn bộ prompt được truyền cho `llm_fn` (cho phép thay LLM thật hoặc mock trong test). Nếu không tìm thấy chunk nào, trả về thông báo thay vì gọi LLM với ngữ cảnh rỗng.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
============================= test session starts ==============================
platform linux -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0 -- /usr/bin/python
cachedir: .pytest_cache
rootdir: /home/aminix/Projects/K4-DAY07-NguyenHaiDang-02963
collecting ... collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED [  2%]
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED [  4%]
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED [  7%]
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED [  9%]
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED [ 11%]
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED [ 14%]
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED [ 16%]
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED [ 19%]
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED [ 21%]
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED   [ 23%]
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED [ 26%]
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED [ 28%]
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED [ 30%]
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED    [ 33%]
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED [ 35%]
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED [ 38%]
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED [ 40%]
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED [ 42%]
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED   [ 45%]
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED [ 47%]
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED [ 50%]
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED [ 52%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED [ 54%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED [ 57%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED [ 59%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED [ 61%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED [ 64%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED [ 66%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED [ 69%]
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED [ 71%]
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED [ 73%]
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED [ 76%]
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED [ 78%]
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED [ 80%]
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED [ 83%]
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED [ 85%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED [ 88%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED [ 90%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED [ 92%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED [ 95%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED [ 97%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED [100%]

============================== 42 passed in 0.12s ==============================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

> Điểm thực tế tính bằng `compute_similarity(MockEmbedder(A), MockEmbedder(B))` — mock embedder 64 chiều. Ghi nhận: kết quả thực tế cho thấy mock embedder gần như **không phản ánh ngữ nghĩa** (điểm xoay quanh 0, thậm chí âm với câu cùng chủ đề).

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Sinh viên đăng ký học phần qua hệ thống SIS. | Sinh viên đăng ký môn học trên cổng SIS. | cao | -0.2924 | Sai |
| 2 | Phí cấp bảng điểm là 50.000 VNĐ mỗi bản. | Học phí học kỳ này đã được thanh toán đầy đủ. | thấp | -0.1219 | Đúng |
| 3 | Thư viện mở cửa lúc 8 giờ sáng. | Sách tham khảo có thể mượn tại quầy thủ thư. | cao | 0.1020 | Sai |
| 4 | Điểm tối thiểu để chuyển đổi tín chỉ là C. | Chuyển đổi tín chỉ cần nội dung tương đương 70%. | cao | 0.0482 | Sai |
| 5 | VinUni nằm tại Hà Nội. | Máy tính để bàn chạy hệ điều hành Linux. | thấp | 0.0095 | Đúng |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Bất ngờ nhất là cặp 1 và 4: hai câu rõ ràng cùng chủ đề (đăng ký qua SIS; chuyển đổi tín chỉ) lại cho điểm gần 0 hoặc âm. Điều này cho thấy **mock embedder không biểu diễn ngữ nghĩa** — nó chỉ băm MD5 chính xác chuỗi ký tự, nên chỉ những chuỗi trùng khớp gần như nguyên văn mới đạt điểm cao (identical vector = 1.0 trong test). Ngược lại, embedding thật (sentence-transformers/OpenAI) học được ngữ nghĩa nhờ huấn luyện trên hàng tỷ câu, nên hai câu cùng nghĩa dù khác từ vựng vẫn ở gần nhau. Đây là lý do benchmark dùng mock embedder cần chuyển sang embedder thật để có retrieval có ý nghĩa.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của tôi — chiến lược **`FixedSizeChunker(chunk_size=500, overlap=50)`** (thành viên 2) với mock embedder trên bộ tài liệu `data/VinUni`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Tối đa bao nhiêu tín chỉ được phép chuyển vào chương trình đại học tại VinUni? | `english-language-requirements-for-undergraduate-admissions` — tiêu đề chính sách tiếng Anh đầu vào | 0.2617 |️doc `chuyen-doi-tin-chi` chỉ ở hạng 3 | Trả lời bằng tiêu đề chính sách tiếng Anh, không có con số "60 tín chỉ" |
| 2 | Học phần cần đáp ứng mức tương đương nội dung và điểm tối thiểu nào để được xem xét chuyển đổi tín chỉ? | `chinh-sach-quy-dinh` — "…Hướng dẫn chuyển đổi chương trình học. Cung cấp chính sách, điề…" | 0.3481 | (gold doc `chuyen-doi-tin-chi` không có trong top-3) | Trả lời về chuyển đổi chương trình học, không nhắc "70% / điểm C" |
| 3 | Trên SIS cần thao tác thế nào để hoàn tất đăng ký môn và trạng thái nào xác nhận đăng ký thành công? | `chinh-sach-quy-dinh` — "Quy chế học thuật cho chương trình Tiến sĩ…" | 0.2445 | (gold doc `thoi-khoa-bieu` không có trong top-3) | Trả lời về quy chế Tiến sĩ, không có "Add/Register/Registered" |
| 4 | Yêu cầu bảng điểm hoặc thư xác nhận thường mất bao lâu và phí mỗi bản là bao nhiêu? | `chinh-sach-quy-dinh` — "Quy chế học thuật cho chương trình Cử nhân chính quy…" | 0.3436 | doc `yeu-cau-cap-bang-diem` ở hạng 2 nhưng chunk không trả lời | Trả lời về quy chế Cử nhân, không có "2–3 ngày / 50.000 VNĐ" |
| 5 | Cần thực hiện những bước nào để đăng ký học phần? (lọc `audience=student`) | `chuyen-doi-tin-chi` — "Chuyển đổi tín chỉ - Registrar…" | 0.1736 | doc `thoi-khoa-bieu-dang-ky-hoc-phan` ở hạng 2 nhưng chunk sai | Trả lời về chuyển đổi tín chỉ, thiếu các bước SIS (Add → Register → Your Class Schedule) |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 

>3 / 5 theo **đúng doc** (Q1 hạng 3, Q4 hạng 2, Q5 hạng 2) — nhưng **0 / 5** theo **chunk chứa câu trả lời**: với mock embedder, không câu nào truy xuất được chunk đủ các answer markers. Đây là giới hạn của mock embedder (băm MD5, không hiểu ngữ nghĩa), không phải lỗi chunking.

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Cả 4 thành viên chạy cùng bộ 5 câu hỏi trên cùng tài liệu với 4 chiến lược khác nhau, và tôi học được nhiều nhất từ việc so sánh đó: (1) **HeadingChunker** tách theo tiêu đề mục rồi đệ quy các mục dài, khai thác đúng cấu trúc trang chính sách VinUni nên sinh ít chunk nhiễu hơn hẳn RecursiveChunker thuần của thành viên 3 (76 vs 822 chunk trên cùng một tài liệu lúc chạy baseline); (2) chiến lược **FixedSizeChunker của tôi** cắt theo đúng số ký tự nên có thể cắt đứt giữa câu — **SentenceChunker** của thành viên 4 giữ trọn câu nên đoạn mạch lạc hơn, còn overlap=50 của tôi giúp giảm mất ngữ cảnh ở biên giới chunk; (3) lọc `audience=student` làm Q5 của nhóm gọn hơn — metadata thực sự có giá trị khi corpora có nhiều `audience`. Bài học lớn nhất: chunking nên bám theo cấu trúc tài liệu của domain, và để so sánh công bằng giữa các thành viên thì phải chạy chung một embedder thật (local/openai/gemini) thay vì mock.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 4 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 8 / 10 |
| **Tổng phần cá nhân** | **57 / 60** |