"""
Task 6 — Lexical Search Module (BM25).

Mặc định sử dụng BM25. Nếu dùng phương pháp khác (TF-IDF, Elasticsearch,
Weaviate BM25 built-in), hãy giải thích cơ chế trong buổi demo → +5 bonus.

Cài đặt:
    pip install rank-bm25

BM25 hoạt động thế nào:
    - Term Frequency (TF): từ xuất hiện nhiều trong document → điểm cao
    - Inverse Document Frequency (IDF): từ hiếm → quan trọng hơn
    - Document length normalization: document dài không bị ưu tiên quá mức
    - Formula: score(q,d) = Σ IDF(qi) * (tf(qi,d) * (k1+1)) / (tf(qi,d) + k1*(1-b+b*|d|/avgdl))
    - k1=1.5 (term saturation), b=0.75 (length normalization)
"""

import re
from pathlib import Path

from rank_bm25 import BM25Okapi

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"

# Corpus + index được nạp lazy (1 lần) và cache lại giữa các lần gọi lexical_search
CORPUS: list[dict] = []
_BM25_INDEX: BM25Okapi | None = None

_TOKEN_RE = re.compile(r"[a-zA-ZÀ-ỹà-ỹ0-9]+")


def _tokenize(text: str) -> list[str]:
    """Tokenize đơn giản: lowercase + tách theo chữ/số (giữ được dấu tiếng Việt)."""
    return _TOKEN_RE.findall(text.lower())


def load_corpus() -> list[dict]:
    """
    Đọc toàn bộ markdown files từ data/standardized/ thành corpus cho BM25.

    Returns:
        List of {'content': str, 'metadata': {'source': str, 'type': str}}
    """
    corpus = []
    for md_file in STANDARDIZED_DIR.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        doc_type = "legal" if "legal" in md_file.parts else "news"
        corpus.append({
            "content": content,
            "metadata": {"source": md_file.name, "type": doc_type},
        })
    return corpus


def build_bm25_index(corpus: list[dict]) -> BM25Okapi:
    """
    Xây dựng BM25 index từ corpus.

    Args:
        corpus: List of {'content': str, 'metadata': dict}

    Returns:
        BM25Okapi index đã fit trên corpus.
    """
    tokenized_corpus = [_tokenize(doc["content"]) for doc in corpus]
    return BM25Okapi(tokenized_corpus)


def _ensure_index_ready() -> BM25Okapi:
    """Nạp corpus + build index nếu chưa có (cache trong module-level state)."""
    global CORPUS, _BM25_INDEX

    if _BM25_INDEX is not None:
        return _BM25_INDEX

    CORPUS = load_corpus()
    if not CORPUS:
        raise RuntimeError(
            f"Không tìm thấy file .md nào trong {STANDARDIZED_DIR}. "
            "Chạy Task 3 (convert markdown) trước."
        )

    _BM25_INDEX = build_bm25_index(CORPUS)
    return _BM25_INDEX


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """
    Tìm kiếm từ khóa sử dụng BM25.

    Args:
        query: Câu truy vấn
        top_k: Số lượng kết quả tối đa

    Returns:
        List of {
            'content': str,
            'score': float,      # BM25 score
            'metadata': dict
        }
        Sorted by score descending.
    """
    bm25 = _ensure_index_ready()

    tokenized_query = _tokenize(query)
    scores = bm25.get_scores(tokenized_query)

    ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

    results = []
    for idx in ranked_indices[:top_k]:
        if scores[idx] <= 0:
            continue
        results.append({
            "content": CORPUS[idx]["content"],
            "score": float(scores[idx]),
            "metadata": CORPUS[idx]["metadata"],
        })
    return results


if __name__ == "__main__":
    # Test
    results = lexical_search("tuition fee payment methods", top_k=5)
    for r in results:
        print(f"[{r['score']:.3f}] {r['content'][:100]}...")
