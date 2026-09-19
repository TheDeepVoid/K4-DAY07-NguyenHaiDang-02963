from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from src import (
    EMBEDDING_PROVIDER_ENV,
    GEMINI_EMBEDDING_MODEL,
    LOCAL_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
    ChunkingStrategyComparator,
    Document,
    EmbeddingStore,
    GeminiEmbedder,
    LocalEmbedder,
    OpenAIEmbedder,
    RecursiveChunker,
    _mock_embed,
)

DATA_DIR = Path("data/VinUni")
TOP_K = 3


class HeadingChunker:
    """Split VinUni policy pages by section heading, then recursively split long sections."""

    SECTION_HEADINGS = {
        "Danh mục chính sách học thuật:",
        "Các Loại Tài Liệu Có Thể Yêu Cầu",
        "Cách Yêu Cầu Tài Liệu",
        "Chi Phí & Giao Nhận",
        "Lưu ý Quan trọng",
        "Khi nào nên gửi yêu cầu chuyển đổi tín chỉ",
        "Cách thức gửi yêu cầu",
        "Điều kiện được xem xét chuyển đổi tín chỉ",
        "Các kỳ thi nâng cao cấp trung học",
        "Các lưu ý quan trọng",
        "Các chính sách liên quan",
        "Hướng dẫn đăng ký môn học",
        "Các bước quan trọng",
        "Quy trình đăng ký môn học",
        "Cách sử dụng SIS để đăng ký môn học",
        "Xử lý sự cố khi đăng ký",
        "Lưu ý bổ sung",
        "Thi cử tại VinUni",
        "Tìm hiểu về điểm số",
        "Hệ điểm",
        "Cách tính GPA",
        "1. PURPOSE",
        "2. AREA OF APPLICATION",
        "3. CONTENT",
        "3.1. General principles",
        "3.2. Recognized English language proficiency mechanisms",
        "3.2.1. English language proficiency tests",
        "3.2.2. Citizenship/resident status",
        "3.2.3. Prior study",
        "4. ENGLISH PROFICIENCY VARIATIONS AND CONDITIONAL ADMISSION",
        "5. ROLES AND RESPONSIBILITIES MATRIX",
    }

    def __init__(self, chunk_size: int = 500) -> None:
        self.chunk_size = chunk_size
        self.fallback = RecursiveChunker(chunk_size=chunk_size)

    def _is_heading(self, line: str) -> bool:
        stripped = line.strip()
        return bool(re.match(r"^#{1,6}\s+\S", stripped)) or stripped in self.SECTION_HEADINGS

    def _split_section(self, heading: str, body_lines: list[str]) -> list[str]:
        body = "\n".join(body_lines).strip()
        section = f"{heading}\n{body}".strip() if heading else body
        if not section:
            return []
        if len(section) <= self.chunk_size:
            return [section]

        prefix = f"{heading}\n" if heading else ""
        available_size = max(1, self.chunk_size - len(prefix))
        pieces = RecursiveChunker(chunk_size=available_size).chunk(body)
        return [f"{prefix}{piece}".strip() for piece in pieces]

    def chunk(self, text: str) -> list[str]:
        if not text.strip():
            return []

        sections: list[tuple[str, list[str]]] = []
        heading = ""
        body_lines: list[str] = []
        for line in text.splitlines():
            if self._is_heading(line):
                if any(part.strip() for part in body_lines):
                    sections.append((heading, body_lines))
                heading = line.strip()
                body_lines = []
            else:
                body_lines.append(line)
        if any(part.strip() for part in body_lines):
            sections.append((heading, body_lines))

        chunks: list[str] = []
        for section_heading, section_body in sections:
            chunks.extend(self._split_section(section_heading, section_body))
        return chunks


# Mỗi thành viên chỉ đổi dòng này để dùng chiến lược riêng.
CHUNKER = HeadingChunker(chunk_size=500)


@dataclass(frozen=True)
class BenchmarkCase:
    query: str
    gold_answer: str
    gold_doc_id: str
    answer_markers: tuple[str, ...]
    metadata_filter: dict[str, str] | None = None


BENCHMARK_CASES = [
    BenchmarkCase(
        query="Tối đa bao nhiêu tín chỉ được phép chuyển vào chương trình đại học tại VinUni?",
        gold_answer="Tối đa 60 tín chỉ.",
        gold_doc_id="chuyen-doi-tin-chi",
        answer_markers=("Tối đa 60 tín chỉ",),
    ),
    BenchmarkCase(
        query="Học phần cần đáp ứng mức tương đương nội dung và điểm tối thiểu nào để được xem xét chuyển đổi tín chỉ?",
        gold_answer="Nội dung tương đương ít nhất 70% và điểm tối thiểu là C hoặc tương đương.",
        gold_doc_id="chuyen-doi-tin-chi",
        answer_markers=("tương đương ít nhất 70%", "tối thiểu là C"),
    ),
    BenchmarkCase(
        query="Trên SIS cần thao tác thế nào để hoàn tất đăng ký môn và trạng thái nào xác nhận đăng ký thành công?",
        gold_answer='Nhấn “Add”, sau đó “Register”; trạng thái phải là “Registered”.',
        gold_doc_id="thoi-khoa-bieu-dang-ky-hoc-phan",
        answer_markers=("Add", "Register", "Registered"),
    ),
    BenchmarkCase(
        query="Yêu cầu bảng điểm hoặc thư xác nhận thường mất bao lâu và phí mỗi bản là bao nhiêu?",
        gold_answer="Thông thường 2–3 ngày làm việc, có thể đến 5 ngày vào mùa cao điểm; phí 50.000 VNĐ mỗi bản.",
        gold_doc_id="yeu-cau-cap-bang-diem-va-chung-nhan",
        answer_markers=("2–3 ngày làm việc", "5 ngày làm việc", "50.000 VNĐ / bản"),
    ),
    BenchmarkCase(
        query="Cần thực hiện những bước nào để đăng ký học phần?",
        gold_answer="Đăng nhập SIS, mở Course Registration, tìm môn, nhấn Add rồi Register và kiểm tra Your Class Schedule.",
        gold_doc_id="thoi-khoa-bieu-dang-ky-hoc-phan",
        answer_markers=("Đăng nhập vào SIS", "Add", "Register", "Your Class Schedule"),
        metadata_filter={"audience": "student"},
    ),
]


def parse_document(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) != 3:
        raise ValueError(f"Frontmatter không hợp lệ: {path}")

    metadata: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata, parts[2].strip()


def build_embedder():
    load_dotenv(override=False)
    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "mock").strip().lower()
    try:
        if provider == "local":
            return LocalEmbedder(os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL))
        if provider == "openai":
            return OpenAIEmbedder(os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL))
        if provider == "gemini":
            return GeminiEmbedder(os.getenv("GEMINI_EMBEDDING_MODEL", GEMINI_EMBEDDING_MODEL))
    except Exception as error:
        print(f"Không thể khởi tạo embedder {provider}: {error}")
        print("Chuyển sang mock embedder.")
    return _mock_embed


def load_chunk_documents(chunker) -> list[Document]:
    documents: list[Document] = []
    for path in sorted(DATA_DIR.glob("*.md")):
        metadata, content = parse_document(path)
        for index, chunk in enumerate(chunker.chunk(content)):
            documents.append(
                Document(
                    id=f"{path.stem}#{index}",
                    content=chunk,
                    metadata={**metadata, "doc_id": path.stem, "chunk_index": index},
                )
            )
    return documents


def print_baseline() -> None:
    comparator = ChunkingStrategyComparator()
    baseline_paths = [
        DATA_DIR / "thoi-khoa-bieu-dang-ky-hoc-phan.md",
        DATA_DIR / "chuyen-doi-tin-chi.md",
        DATA_DIR / "yeu-cau-cap-bang-diem-va-chung-nhan.md",
    ]
    print("=== BASELINE ANALYSIS (không gồm frontmatter) ===")
    for path in baseline_paths:
        _, content = parse_document(path)
        comparison = comparator.compare(content, chunk_size=500)
        for strategy, stats in comparison.items():
            print(
                f"{path.stem:42} {strategy:14} "
                f"count={stats['count']:3} avg_length={stats['avg_length']:.2f}"
            )
    print()


def contains_answer(result: dict, markers: tuple[str, ...]) -> bool:
    content = result["content"].casefold()
    return all(marker.casefold() in content for marker in markers)


def print_results(label: str, case: BenchmarkCase, results: list[dict]) -> None:
    print(f"  {label}:")
    for rank, result in enumerate(results, start=1):
        metadata = result["metadata"]
        preview = " ".join(result["content"].split())[:180]
        print(
            f"    {rank}. score={result['score']:.4f} "
            f"doc_id={metadata.get('doc_id')} chunk={result['id']}"
        )
        print(f"       {preview}")

    gold_rank = next(
        (
            rank
            for rank, result in enumerate(results, start=1)
            if result["metadata"].get("doc_id") == case.gold_doc_id
        ),
        None,
    )
    answer_rank = next(
        (rank for rank, result in enumerate(results, start=1) if contains_answer(result, case.answer_markers)),
        None,
    )
    print(f"    gold_doc_rank={gold_rank or 'không có'}; answer_chunk_rank={answer_rank or 'không có'}")


def run_benchmark() -> None:
    print_baseline()
    embedder = build_embedder()
    documents = load_chunk_documents(CHUNKER)
    store = EmbeddingStore(collection_name="vinuni_benchmark", embedding_fn=embedder)
    store.add_documents(documents)

    print("=== BENCHMARK ===")
    print(f"Chunker: {CHUNKER.__class__.__name__}")
    print(f"Embedding backend: {getattr(embedder, '_backend_name', embedder.__class__.__name__)}")
    print(f"Số tài liệu nguồn: {len(list(DATA_DIR.glob('*.md')))}")
    print(f"Số chunk đã nạp: {store.get_collection_size()}")
    print()

    for index, case in enumerate(BENCHMARK_CASES, start=1):
        print(f"Q{index}: {case.query}")
        print(f"  Gold answer: {case.gold_answer}")
        if case.metadata_filter:
            filtered = store.search_with_filter(case.query, top_k=TOP_K, metadata_filter=case.metadata_filter)
            unfiltered = store.search(case.query, top_k=TOP_K)
            print_results(f"Có filter {case.metadata_filter}", case, filtered)
            print_results("Không filter", case, unfiltered)
        else:
            results = store.search_with_filter(case.query, top_k=TOP_K, metadata_filter=None)
            print_results("Top-3", case, results)
        print()


if __name__ == "__main__":
    run_benchmark()
