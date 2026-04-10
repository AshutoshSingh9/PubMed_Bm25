# Clinical Intelligence NLP

**An AI-powered reasoning engine and unified dashboard that modernizes how general physicians and medical professionals interact with the PubMed biomedical databank.**

![Clinical Intelligence Dashboard](https://img.shields.io/badge/Status-Active-success) ![License](https://img.shields.io/badge/License-Open_Source-blue)

## Why This Engine Outperforms PubMed's Native Search

PubMed is an incredibly vast and powerful academic database, but its search engine was built decades ago for rigid, boolean-literate researchers. Our **Clinical Intelligence NLP** architecture completely replaces this outdated retrieval paradigm with modern Machine Learning:

### 1. Zero-Friction Natural Language Queries (LLM Translation)
* **The PubMed Problem:** If you ask PubMed, *"Why would a doctor order a D-dimer test?"*, it searches for the literal string `"doctor order d dimer test"` and returns **0 results**. You must learn its strict MeSH boolean syntax to get answers.
* **Our Solution:** This app features a real-time **Groq Llama-3.3-70B translation layer**. It intercepts your natural language, surgically strips conversational filler, and translates your query into a pristine, optimized academic query (e.g., `'d-dimer test'`) in less than 300ms before ever touching PubMed's servers.

### 2. Hybrid Reciprocal Rank Fusion (RRF)
* **The PubMed Problem:** Classic PubMed relies purely on keyword overlaps and publication recency.
* **Our Solution:** Incoming papers are automatically indexed locally into a **ChromaDB Vector Store** using high-dimensional `ONNX` semantic embeddings. The system simultaneously runs:
  1. **Dense Vector Search:** Finds papers conceptually related to your query, even if they don't share identical metadata.
  2. **Sparse BM25 Search:** Performs highly-accurate statistical keyword matching.
  *It mathematically merges both signals using Reciprocal Rank Fusion (RRF) to rank papers by true clinical relevance, not just keyword occurrence.*

### 3. Automated Diagnostic Reasoning Pipeline
Instead of just displaying abstracts, the engine funnels retrieved literature into a **robust 3-Stage LLM Pipeline**:
1. **Diagnostician Stage:** Projects a statistical differential diagnosis matrix based on the literature.
2. **Critic Stage:** Audits the Diagnostician's clinical reasoning for flaws or biases.
3. **Safety Validator:** Strictly scans treatments for contraindications, immediately flagging harmful interactions.

---

## Technical Architecture

* **Frontend Engine:** React, Vite, TailwindCSS (shadcn/ui aesthetics), Framer Motion
* **Backend API:** Python, FastAPI, Uvicorn
* **Large Language Models:** Groq Cloud (`llama-3.3-70b-versatile`)
* **Datastore/Embeddings:** ChromaDB (Native `all-MiniLM-L6-v2` ONNX execution, zero PyTorch dependency)
* **Bio-Retrieval:** NCBI Entrez API

---

## 🚀 Getting Started

### 1. Environment Configuration
Create a `.env` file in the root directory:
```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
NCBI_EMAIL=your_email@example.com
```

### 2. Run the Backend (FastAPI + ChromaDB)
We utilize `uv` for hyper-fast Python package execution.
```bash
uv run python dashboard_api.py
```
*(Optionally, test the diagnostic pipeline headlessly via `uv run python console_search.py`)*

### 3. Run the Frontend Dashboard (React + Vite)
In a secondary terminal window:
```bash
cd nlp_dashboard
npm install
npm run dev
```

Visit the designated local host address (e.g., `http://localhost:5173`) to launch the Visual Semantic Discovery dashboard.
