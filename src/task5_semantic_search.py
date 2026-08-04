"""
Task 5 — Semantic Search Module + HyDE.

Viết module tìm kiếm ngữ nghĩa (dense retrieval) trên vector store.

Yêu cầu:
    - Input: query string + top_k
    - Output: danh sách chunks có score, sorted descending
    - Phải tương thích với embedding model và vector store ở Task 4

HyDE (Hypothetical Document Embeddings):
    Thay vì embed thẳng câu hỏi ngắn của user (thường thiếu ngữ cảnh, embedding
    kém match với document thật), nhờ LLM sinh ra 1 đoạn văn "giả định là câu trả
    lời" cho câu hỏi đó, rồi embed đoạn giả định này để search. Một đoạn "trả lời
    giả định" có văn phong gần với document thật trong corpus hơn câu hỏi ngắn,
    nên thường match tốt hơn trong không gian vector — đặc biệt khi corpus dùng
    ngôn ngữ trang trọng (chính sách, quy định) còn câu hỏi user lại thông tục.
"""

import os

from dotenv import load_dotenv

from .task4_chunking_indexing import (
    CHROMA_DIR,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
)

load_dotenv()

# TODO: Model LLM dùng để sinh hypothetical document cho HyDE (OpenRouter model ID)
HYDE_LLM_MODEL = "openai/gpt-4o-mini"

# Model + collection dùng lazy-load, cache lại module-level để không load lại mỗi query
_embedding_model = None
_chroma_collection = None


def _get_embedding_model():
    """Lazy-load embedding model (cùng model đã dùng để index ở Task 4)."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    return _embedding_model


def _get_collection():
    """Lazy-load ChromaDB collection đã index ở Task 4."""
    global _chroma_collection
    if _chroma_collection is None:
        import chromadb

        if not CHROMA_DIR.exists():
            raise RuntimeError(
                f"Chưa tìm thấy {CHROMA_DIR} — chạy Task 4 (chunking & indexing) trước."
            )
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _chroma_collection = client.get_collection(name=COLLECTION_NAME)
    return _chroma_collection


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """
    Tìm kiếm ngữ nghĩa sử dụng vector similarity.

    Args:
        query: Câu truy vấn
        top_k: Số lượng kết quả tối đa

    Returns:
        List of {
            'content': str,      # Nội dung chunk
            'score': float,      # Cosine similarity score
            'metadata': dict     # source, doc_type, chunk_index
        }
        Sorted by score descending.
    """
    model = _get_embedding_model()
    query_vector = model.encode(query).tolist()

    collection = _get_collection()
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    output = []
    documents = results["documents"][0] if results["documents"] else []
    metadatas = results["metadatas"][0] if results["metadatas"] else []
    distances = results["distances"][0] if results["distances"] else []

    for doc, meta, dist in zip(documents, metadatas, distances):
        # ChromaDB trả cosine DISTANCE (0 = giống hệt), chuyển sang similarity [0,1]
        score = max(0.0, 1.0 - dist)
        output.append({"content": doc, "score": round(score, 4), "metadata": meta})

    output.sort(key=lambda x: x["score"], reverse=True)
    return output[:top_k]


# =============================================================================
# HyDE — Hypothetical Document Embeddings
# =============================================================================

HYDE_PROMPT = """Viết một đoạn văn ngắn (3-5 câu) trả lời câu hỏi sau, như thể trích
từ một tài liệu chính sách/thông báo của trường đại học. Không cần đúng sự thật —
chỉ cần đúng văn phong và cấu trúc của tài liệu chính thức, để dùng làm truy vấn
tìm kiếm ngữ nghĩa.

Câu hỏi: {query}

Đoạn văn giả định:"""


def generate_hypothetical_document(query: str) -> str:
    """
    Sinh 1 đoạn văn giả định (hypothetical document) trả lời cho query, dùng LLM.

    Đoạn văn này KHÔNG cần đúng sự thật — chỉ cần có văn phong/cấu trúc giống
    document thật trong corpus, để embedding của nó match tốt hơn embedding của
    câu hỏi gốc (thường ngắn, thiếu ngữ cảnh).
    """
    from openai import OpenAI

    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Thiếu OPENROUTER_API_KEY hoặc OPENAI_API_KEY trong .env")

    client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

    response = client.chat.completions.create(
        model=HYDE_LLM_MODEL,
        messages=[{"role": "user", "content": HYDE_PROMPT.format(query=query)}],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def semantic_search_hyde(query: str, top_k: int = 10) -> list[dict]:
    """
    Semantic search dùng HyDE: sinh hypothetical document từ query, sau đó dùng
    chính đoạn văn đó (thay vì query gốc) để tìm kiếm ngữ nghĩa.

    Args:
        query: Câu truy vấn gốc của user
        top_k: Số lượng kết quả tối đa

    Returns:
        Cùng format với semantic_search().
    """
    hypothetical_doc = generate_hypothetical_document(query)
    return semantic_search(hypothetical_doc, top_k=top_k)


if __name__ == "__main__":
    # Test
    results = semantic_search("what is the tuition fee", top_k=5)
    for r in results:
        print(f"[{r['score']:.3f}] {r['content'][:100]}...")
