# 🤖 FAQ Genius: Multi-Tenant FAQ RAG Chatbot

A high-performance, production-ready Retrieval-Augmented Generation (RAG) chatbot engine. This full-stack application utilizes **FastAPI** for a modular backend, **Streamlit** for an interactive user interface, and **ChromaDB** for efficient vector storage. The architecture seamlessly taps into **NVIDIA NIM microservices** for fast embeddings and inference by utilizing an OpenAI client compliance layer.

Designed to be hybrid-ready, it deploys seamlessly both as a local multi-container system via Docker Compose and as a unified single-container application on **Hugging Face Spaces**.

---

## 🛠️ Tech Stack & Architecture

* **Frontend UI:** Streamlit (Python-driven interactive interface)
* **Backend Framework:** FastAPI (Asynchronous REST API framework)
* **Vector Database:** ChromaDB (Embedded local vector store management)
* **LLM Infrastructure:** NVIDIA NIM microservices
    * **Embedding Model:** `nvidia/llama-nemotron-embed-1b-v2`
    * **LLM Model:** `openai/gpt-oss-20b` (Wrapped via standard OpenAI SDK compliance)
* **Containerization:** Docker & Bash Process Controller (`start.sh`)

---

## 📁 Project Structure

```text
├── data/
│   └── faqs.json            # Target raw structural knowledge graph data
├── src/
│   ├── __init__.py
│   ├── database.py         # VectorDBManager & Custom NVIDIA Embeddings layer
│   ├── engine.py           # RAG retrieval context injection & prompt pipeline
│   └── main.py             # FastAPI App instance and Lifespan endpoint routes
├── frontend.py             # Streamlit application UI layer 
├── Dockerfile              # Cross-platform production multi-process build script
├── start.sh                # Concurrent multi-process worker runner (FastAPI + Streamlit)
├── requirements.txt        # Hardened dependency locklist
└── .dockerignore           # Production container build optimization filter
