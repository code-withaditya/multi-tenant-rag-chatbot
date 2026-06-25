# 📋 FAQ Genius - Project Roadmap & TODO List

Track features, pipeline enhancements, and architectural upgrades for the Multi-Tenant FAQ RAG Chatbot stack.

---

## 🚀 Phase 1: Core UX & Interface Enhancements
- [ ] **Chat Session History:** Add `st.session_state` persistence in `frontend.py` so conversations don't vanish on page refresh.
- [ ] **Dynamic FAQ Uploader:** Implement a file upload button (`.json` or `.csv`) in Streamlit that dynamically triggers backend indexing instead of relying on a hardcoded file.
- [ ] **Streaming Responses:** Refactor the FastAPI endpoint and Streamlit chat box to stream text tokens using `EventSourceResponse` for a snappy, ChatGPT-like feel.
- [ ] **Token Usage Tracker:** Display metadata showing processing time, retrieval latency, and estimated token usage for each query.

---

## 🏢 Phase 2: True Multi-Tenancy Architecture
- [ ] **Tenant Isolation Layer:** Modify `src/database.py` to support dynamic ChromaDB collections named cleanly by tenant IDs instead of a singular default collection.
- [ ] **API Authentication:** Secure FastAPI routes using JWT tokens or API keys to ensure Tenant A can never read or query Tenant B's vector space.
- [ ] **Tenant Admin Dashboard:** Build a separate Streamlit view allowing specific tenants to manage, update, or clear out their custom FAQ knowledge bases.

---

## 🧠 Phase 3: Advanced RAG Optimization
- [ ] **Hybrid Search integration:** Combine ChromaDB semantic vector search with keyword-based BM25 lexical search to catch exact keyword matches.
- [ ] **NVIDIA NIM Re-ranking Layer:** Introduce an execution step utilizing an NVIDIA NeMo re-ranking microservice model (e.g., `nvidia/rerank-qa-mistral-4b`) to optimize context relevance prior to LLM synthesis.
- [ ] **Query Expansion / Reformulation:** Use a lightweight LLM call to rewrite ambiguous user follow-up questions into fully contextual search queries before hitting the vector database.
- [ ] **Evaluation Framework:** Integrate an evaluation library like Ragas to automatically benchmark Context Precision, Context Recall, and Faithfulness scores.

---

## 🛡️ Phase 4: Production Hardening & CI/CD
- [ ] **Unified Routing Config:** Implement a centralized `config.py` using Pydantic Settings to handle the local (`backend:8000`) vs. production (`localhost:8000`) URL switch automatically based on environment flags.
- [ ] **Database Migration System:** Write a script to automatically verify, backup, or flush the local persistence layer (`./chroma_db`) across rebuild cycles.
- [ ] **Automated Integration Tests:** Write pytest configurations validating core FastAPI `/api/v1/chat` and database initialization routines.
- [ ] **Comprehensive Logging Integration:** Replace standard print statements with structured JSON logging to monitor production pipeline crashes efficiently.