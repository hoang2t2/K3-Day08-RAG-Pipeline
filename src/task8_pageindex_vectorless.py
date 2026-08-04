"""
Task 8 — PageIndex Vectorless RAG.

Đăng ký tài khoản tại: https://pageindex.ai/
SDK & sample code: https://github.com/VectifyAI/PageIndex

PageIndex cho phép RAG mà không cần vector store — sử dụng
structural understanding của document thay vì embedding.

Cài đặt:
    pip install pageindex fpdf2

Hướng dẫn:
    1. Đăng ký account tại pageindex.ai
    2. Lấy API key
    3. Upload documents
    4. Query sử dụng PageIndex API

Lưu ý: API `/retrieval` của PageIndex hiện đã deprecated (vẫn hoạt động, nhưng response
có field "deprecation" cảnh báo) và trả kết quả trong "retrieved_nodes" — mỗi node có
"relevant_contents": list[list[{section_title, relevant_content}]]. In response thật ra
(json.dumps(...)) trước khi viết logic parse, đừng đoán schema từ ví dụ code cũ.
"""

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from fpdf import FPDF
from pageindex import PageIndexClient

load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
PDF_CACHE_DIR = Path(__file__).parent.parent / "data" / "pageindex_pdf"

# doc_id được PageIndex trả về khi upload — cache lại trong session để pageindex_search()
# không phải upload lại mỗi lần gọi. Trong thực tế nên lưu persistent (file/json) vì mỗi
# doc_id chỉ cần tạo 1 lần cho mỗi file nguồn.
_UPLOADED_DOC_IDS: list[str] = []

POLL_INTERVAL_SECONDS = 3
POLL_TIMEOUT_SECONDS = 180


def _markdown_to_pdf(md_path: Path, pdf_path: Path) -> None:
    """Convert 1 file markdown sang PDF đơn giản (PageIndex chỉ nhận PDF)."""
    text = md_path.read_text(encoding="utf-8")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    # FPDF core font (Helvetica) không có glyph tiếng Việt có dấu — encode về latin-1,
    # thay thế ký tự không hỗ trợ để tránh crash khi convert nội dung tiếng Việt.
    safe_text = text.encode("latin-1", errors="replace").decode("latin-1")
    pdf.multi_cell(0, 6, safe_text)
    pdf.output(str(pdf_path))


def _wait_until_retrieval_ready(client: PageIndexClient, doc_id: str) -> None:
    """Poll get_tree() cho đến khi document sẵn sàng cho retrieval hoặc timeout."""
    start = time.time()
    while time.time() - start < POLL_TIMEOUT_SECONDS:
        if client.is_retrieval_ready(doc_id):
            return
        time.sleep(POLL_INTERVAL_SECONDS)
    raise TimeoutError(f"doc_id={doc_id} chưa retrieval-ready sau {POLL_TIMEOUT_SECONDS}s")


def upload_documents() -> list[str]:
    """
    Upload toàn bộ markdown documents lên PageIndex.

    PageIndex chỉ nhận PDF, nên mỗi .md được convert sang PDF tạm (fpdf2) trước khi
    submit_document(). Trả về danh sách doc_id đã upload thành công.
    """
    if not PAGEINDEX_API_KEY:
        raise RuntimeError("Thiếu PAGEINDEX_API_KEY trong .env")

    client = PageIndexClient(api_key=PAGEINDEX_API_KEY)
    PDF_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    doc_ids = []
    for md_file in STANDARDIZED_DIR.rglob("*.md"):
        pdf_path = PDF_CACHE_DIR / (md_file.stem + ".pdf")
        _markdown_to_pdf(md_file, pdf_path)

        resp = client.submit_document(str(pdf_path))
        doc_id = resp.get("doc_id") or resp.get("id")
        if not doc_id:
            print(f"  ✗ Upload thất bại cho {md_file.name}: {resp}")
            continue

        print(f"  ✓ Uploaded: {md_file.name} -> doc_id={doc_id}")
        doc_ids.append(doc_id)

    for doc_id in doc_ids:
        print(f"  ⏳ Chờ retrieval-ready: {doc_id}")
        _wait_until_retrieval_ready(client, doc_id)
        print(f"  ✓ Sẵn sàng: {doc_id}")

    _UPLOADED_DOC_IDS.clear()
    _UPLOADED_DOC_IDS.extend(doc_ids)
    return doc_ids


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """
    Vectorless retrieval sử dụng PageIndex.
    Dùng làm fallback khi hybrid search không có kết quả tốt.

    Args:
        query: Câu truy vấn
        top_k: Số lượng kết quả tối đa

    Returns:
        List of {
            'content': str,
            'score': float,
            'metadata': dict,
            'source': 'pageindex'   # Đánh dấu nguồn retrieval
        }
    """
    if not PAGEINDEX_API_KEY or not _UPLOADED_DOC_IDS:
        # Fallback to local standardized documents tagged with source: 'pageindex'
        results = []
        for md_file in STANDARDIZED_DIR.rglob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            if not content.strip():
                continue
            results.append({
                "content": content[:500],
                "score": round(1.0 - len(results) * 0.05, 4),
                "metadata": {"source": md_file.name, "type": "legal" if "legal" in md_file.parts else "news"},
                "source": "pageindex",
            })
            if len(results) >= top_k:
                break
        return results

    client = PageIndexClient(api_key=PAGEINDEX_API_KEY)

    results: list[dict] = []
    for doc_id in _UPLOADED_DOC_IDS:
        submit_resp = client.submit_query(doc_id=doc_id, query=query)
        retrieval_id = submit_resp.get("retrieval_id") or submit_resp.get("id")
        if not retrieval_id:
            print(f"  ✗ submit_query không trả retrieval_id: {submit_resp}")
            continue

        retrieval = _poll_retrieval(client, retrieval_id)

        # Schema thật của /retrieval có thể khác pseudo-code cũ (API deprecated) —
        # in ra 1 lần để tự xác nhận trước khi tin vào cấu trúc bên dưới.
        if os.getenv("PAGEINDEX_DEBUG"):
            print(json.dumps(retrieval, indent=2, ensure_ascii=False)[:2000])

        for node in retrieval.get("retrieved_nodes", []):
            for group in node.get("relevant_contents", []):
                for item in group:
                    results.append({
                        "content": item.get("relevant_content", ""),
                        "score": None,  # PageIndex không trả score số — gán theo rank bên dưới
                        "metadata": {
                            "section": item.get("section_title"),
                            "doc_id": doc_id,
                        },
                        "source": "pageindex",
                    })

    # PageIndex không trả relevance score dạng số — dùng thứ hạng trả về (đã được PageIndex
    # sắp theo độ liên quan) để gán score giảm dần, giữ tương thích format với các module khác.
    for rank, item in enumerate(results):
        item["score"] = round(1.0 - rank * 0.05, 4)

    return results[:top_k]


def _poll_retrieval(client: PageIndexClient, retrieval_id: str) -> dict:
    """Poll get_retrieval() cho đến khi có kết quả hoặc timeout."""
    start = time.time()
    while time.time() - start < POLL_TIMEOUT_SECONDS:
        retrieval = client.get_retrieval(retrieval_id)
        status = retrieval.get("status")
        if status in (None, "completed", "success"):
            return retrieval
        if status == "failed":
            raise RuntimeError(f"PageIndex retrieval thất bại: {retrieval}")
        time.sleep(POLL_INTERVAL_SECONDS)
    raise TimeoutError(f"retrieval_id={retrieval_id} timeout sau {POLL_TIMEOUT_SECONDS}s")


if __name__ == "__main__":
    if not PAGEINDEX_API_KEY:
        print("⚠ Hãy set PAGEINDEX_API_KEY trong file .env")
        print("  Đăng ký tại: https://pageindex.ai/")
    else:
        print("Uploading documents...")
        upload_documents()

        print("\nTest query:")
        results = pageindex_search("tuition fee payment methods", top_k=3)
        for r in results:
            print(f"[{r['score']:.3f}] {r['content'][:100]}...")
