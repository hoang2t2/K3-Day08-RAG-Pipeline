# Bài Tập Nhóm — University Services RAG Chatbot

## Mục Tiêu

Sau khi hoàn thành bài cá nhân, nhóm ngồi lại để xây dựng **1 trong 2 sản phẩm**:

---

## Yêu cầu 1: Sản phẩm nhóm RAG Chatbot

Xây dựng chatbot trả lời câu hỏi về dịch vụ và chính sách đại học liên quan.

**Yêu cầu:**
- Giao diện chat (Streamlit / Gradio / Chainlit)
- Trả lời có citation (dựa trên Task 10)
- Hỗ trợ follow-up questions (conversation memory)
- Hiển thị source documents đã dùng

**Stack gợi ý:**
```
Chainlit/Streamlit → Retrieval (Task 9) → Generation (Task 10) → Display
```

---

## Yêu cầu 2: RAG Evaluation Pipeline

Sử dụng **1 trong 3 framework** sau để evaluate pipeline RAG của nhóm:

### Framework lựa chọn

| Framework | Cài đặt | Đặc điểm |
|-----------|---------|-----------|
| [DeepEval](https://github.com/confident-ai/deepeval) | `pip install deepeval` | Nhiều metric built-in, dễ integrate với pytest |
| [RAGAS](https://github.com/explodinggradients/ragas) | `pip install ragas` | Chuẩn industry cho RAG eval, 3 trục chính |
| [TruLens](https://github.com/truera/trulens) | `pip install trulens` | Dashboard UI, feedback functions mạnh |

### Yêu cầu Evaluation

1. **Tạo Golden Dataset** — tối thiểu 15 cặp Q&A (question, expected_answer, expected_context)
2. **Chạy evaluation** trên toàn bộ golden dataset với các metrics sau:
   - **Faithfulness** — câu trả lời có bám đúng context không?
   - **Answer Relevance** — câu trả lời có đúng câu hỏi không?
   - **Context Recall** — retriever có lấy đủ evidence không?
   - **Context Precision** — trong context lấy về, bao nhiêu % thực sự hữu ích?
3. **So sánh A/B** — chạy eval trên ít nhất 2 config khác nhau (ví dụ: có reranking vs không reranking, hoặc hybrid vs dense-only)
4. **Báo cáo** — bảng điểm + phân tích worst performers + đề xuất cải tiến

Xem code mẫu (DeepEval/RAGAS/TruLens) chi tiết trong `README.md` gốc mục "Yêu cầu 2".

### Deliverable Evaluation

- [ ] File `group_project/evaluation/golden_dataset.json` — 15+ cặp Q&A
- [ ] File `group_project/evaluation/eval_pipeline.py` — script chạy evaluation
- [ ] File `group_project/evaluation/results.md` — bảng điểm + phân tích
- [ ] So sánh A/B ít nhất 2 configs

---

## Yêu Cầu Chung

1. **Tích hợp pipeline** từ bài cá nhân của các thành viên
2. **Demo hoạt động được** trong buổi trình bày (chạy local hoặc deploy)
3. **Evaluation pipeline** chạy được và có báo cáo kết quả
4. **Code push lên repository** chung của nhóm
5. **README** mô tả kiến trúc và phân công (điền bên dưới)

---

## Kiến Trúc Hệ Thống

```mermaid
graph TD
    subgraph Data_Ingestion ["1. Data Ingestion & Standardization"]
        A1[Legal PDF/DOCX] -->|Task 3: MarkItDown| B1[data/standardized/legal/*.md]
        A2[News / Web Articles] -->|Task 2: Crawl4AI| B2[data/standardized/news/*.md]
    end

    subgraph Indexing ["2. Chunking & Indexing"]
        B1 & B2 -->|Task 4: RecursiveCharacterTextSplitter| C1[Document Chunks]
        C1 -->|BAAI/bge-m3 Embedding| C2[(ChromaDB Vector Store)]
        C1 -->|Tokenization & Keyword Map| C3[BM25 Index]
    end

    subgraph Retrieval ["3. Hybrid Retrieval & Reranking"]
        Q[User Query] -->|Task 5: Dense Search| D1[Semantic Candidates]
        Q -->|Task 6: Lexical BM25| D2[Lexical Candidates]
        D1 & D2 -->|Task 9: Fusion / Merge| E1[Merged Candidates]
        E1 -->|Task 7: Reranker| E2[Reranked Top Candidates]
        E2 -->|Confidence Score Check| F1{Score >= Threshold?}
        F1 -->|No| F2[Task 8: PageIndex Vectorless Fallback]
        F1 -->|Yes| G1[Final Context Chunks]
        F2 --> G1
    end

    subgraph Generation ["4. Generation & Chat Interface"]
        G1 -->|Task 10: Reorder - Lost in Middle| H1[Reordered Context]
        H1 -->|Prompt + System Prompt| H2[LLM: OpenRouter / OpenAI / Gemini]
        H2 -->|Response with Citations| I[Streamlit Chatbot App: app.py]
    end
```

---

## Phân Công Công Việc (Nhóm 5 Thành Viên — Chuyên Sâu Retrieval)

| Thành viên | MSSV | Vai trò | Nhiệm vụ chi tiết | Trạng thái |
|-----------|------|---------|-------------------|------------|
| **Đoàn Vũ Hoàng** | 2A202601727 | **Role 1**: Team Leader & RAG Architect | Quản lý chung, ghép code pipeline chính (`supervisor.py` & Task 9) | ✅ Hoàn thành |
| **Nguyễn Mạnh Hưng** | 2A202601829 | **Role 2**: Data & Dense Search Dev | Task 1–3 (Data) + Task 4 (ChromaDB) + Task 5 (Semantic Search & HyDE) | ✅ Hoàn thành |
| **Sùng A Khua** | 2A202601129 | **Role 3**: Sparse Search & Advanced Reranking Dev | Task 6 (BM25/TF-IDF) + Task 7 (RRF Reranking) + Task 8 (PageIndex Fallback) | ✅ Hoàn thành |
| **Lê Hoàng Long** | 2A202601025 | **Role 4**: Frontend & Chatbot Developer | Xây dựng Streamlit Chatbot `app.py` + Task 10 (Generation có Citation) | ✅ Hoàn thành |
| **Đàm Vinh Quang** | 2A202601255 | **Role 5**: Evaluation & QA Engineer | Bộ câu hỏi `golden_dataset.json` + Đánh giá RAGAS & báo cáo so sánh A/B `results.md` | ✅ Hoàn thành |

---

## Hướng Dẫn Chạy

```bash
# Cài đặt dependencies
pip install -r requirements.txt

# Chạy app
streamlit run app.py
# hoặc
chainlit run app.py
```

---

## Lưu ý

Hãy giữ lại repo này nếu như bạn học track 3 giai đoạn 2, chúng ta sẽ phát triển tiếp dự án lên knowledge graph để khắc phục các câu hỏi hóc búa khi có các câu hỏi khó.
