## DocuChat (Backend)

### What this is

FastAPI backend for an AI-powered PDF Q&A system using:

- **LLM**: Groq (LLaMA 3 / Mixtral) via `langchain-groq`
- **Embeddings**: Hugging Face `sentence-transformers`
- **Vector DB**: **MongoDB Atlas Vector Search** (cosine similarity)
- **Framework**: LangChain
- **PDF loading**: `PyPDFLoader`

### Endpoints

- **Required endpoints (spec)**:
  - `POST /upload` (multipart) → ingest PDF, store vectors
  - `POST /chat` (json) → answer using similarity search across all PDFs in a session

- **React UI compatibility endpoints (this repo’s `src/` expects these)**:
  - `GET /api/documents`
  - `POST /api/documents/upload`
  - `GET /api/documents/{documentId}`
  - `DELETE /api/documents/{documentId}`
  - `POST /api/chat/query` (scoped to one selected document)

### MongoDB Atlas Vector Search index (cosine)

Create an Atlas Vector Search index on the **chunks collection** (default: `chunks`) using:

- File: `backend/mongodb_vector_index.json`
- **Index name**: must match `MONGODB_VECTOR_INDEX_NAME` (default: `chunks_vector_index`)
- **Dimensions**: must match `EMBEDDINGS_DIMENSIONS` (default: `384`)

### Setup

1. Create a Python venv and install deps:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Configure env:

```bash
cp env.example .env
```

Then edit `.env` with:
- `GROQ_API_KEY`
- `MONGODB_URI`

3. Create the Atlas Vector Search index (see section above).

### Run

```bash
source .venv/bin/activate
cd ..
python -m backend.main
```

Server starts on `http://localhost:8080`.

### Notes

- **Page references**: each chunk is stored with `metadata={"page": <1-indexed>, "source": <filename>}` and answers include a citations footer like `Citations: file.pdf p.3`.
- **Multiple PDFs per session**: `/chat` searches across all PDFs stored under `session_id`. Pass `session_id` in the JSON body or `X-Session-Id` for `/upload`.


