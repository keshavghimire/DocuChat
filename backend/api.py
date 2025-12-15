from __future__ import annotations

# Keras patch should already be applied by _keras_patch.py imported in main.py
# But we ensure it here as well for safety
import sys
try:
    import tf_keras
    if 'keras' not in sys.modules or sys.modules.get('keras') != tf_keras:
        sys.modules['keras'] = tf_keras
except ImportError:
    pass

import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.chunking import split_into_chunks
from backend.embeddings import get_embeddings
from backend.llm import get_llm
from backend.loaders import load_pdf_pages
from backend.retriever import MongoAtlasVectorRetriever
from backend.settings import Settings, get_settings
from backend.vector_store import (
    create_document_record,
    delete_document_and_chunks,
    ensure_non_vector_indexes,
    get_chunks_collection,
    get_db,
    get_documents_collection,
    get_mongo_client,
    get_document,
    insert_chunks,
    list_documents,
    update_document_status,
    utc_now,
)


class UploadResponse(BaseModel):
    documentId: str
    fileName: str
    fileSize: Optional[int]
    pages: int = 0
    status: str
    errorMessage: Optional[str] = None
    createdAt: str
    updatedAt: str


class ChatTurn(BaseModel):
    role: str = Field(..., description="user|assistant")
    content: str


class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="User session id")
    question: str
    chat_history: Optional[List[ChatTurn]] = None


class ChatResponseSource(BaseModel):
    pageNumber: int
    snippet: str
    similarity: Optional[float] = None
    source: Optional[str] = None
    documentId: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[ChatResponseSource]


class UIChatQueryRequest(BaseModel):
    documentId: str
    question: str


def _safe_session_id(settings: Settings, provided: Optional[str]) -> str:
    return (provided or "").strip() or settings.default_session_id


def _save_upload_to_disk(settings: Settings, document_id: str, upload: UploadFile) -> str:
    """
    Persist upload temporarily so a background task can process it.
    """

    storage_dir = Path(settings.storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)

    file_path = storage_dir / f"{document_id}.pdf"
    with file_path.open("wb") as f:
        shutil.copyfileobj(upload.file, f)

    return str(file_path)


def _validate_upload(settings: Settings, upload: UploadFile) -> None:
    if upload.content_type not in ("application/pdf", "application/octet-stream"):
        # Some browsers send octet-stream for PDFs.
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Enforce size limit when possible (UploadFile doesn't always expose size).
    # If running behind a proxy, also configure max body size there.
    # Here we do a best-effort check using the file descriptor position.
    try:
        pos = upload.file.tell()
        upload.file.seek(0, os.SEEK_END)
        size = upload.file.tell()
        upload.file.seek(pos, os.SEEK_SET)
        if size > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large.")
    except Exception:
        # If we can't determine size, proceed (FastAPI/Uvicorn may enforce limits elsewhere).
        pass


def _docs_to_prompt_context(docs: List[Any]) -> str:
    """
    Turn retrieved chunks into a stable context format that makes citations easy.
    """

    parts: List[str] = []
    for i, d in enumerate(docs, start=1):
        page = d.metadata.get("page")
        source = d.metadata.get("source")
        parts.append(
            f"[CHUNK {i}] SOURCE: {source} | PAGE: {page}\n{d.page_content}".strip()
        )
    return "\n\n---\n\n".join(parts)


def _compact_sources(docs: List[Any]) -> List[ChatResponseSource]:
    sources: List[ChatResponseSource] = []
    for d in docs:
        page = d.metadata.get("page")
        if page is None:
            continue
        snippet = (d.page_content or "").strip().replace("\n", " ")
        snippet = snippet[:240] + ("..." if len(snippet) > 240 else "")
        sources.append(
            ChatResponseSource(
                pageNumber=int(page),
                snippet=snippet,
                similarity=d.metadata.get("similarity"),
                source=d.metadata.get("source"),
                documentId=d.metadata.get("documentId"),
            )
        )

    # Deduplicate (source,page) pairs while preserving order.
    seen = set()
    unique: List[ChatResponseSource] = []
    for s in sources:
        key = (s.source, s.pageNumber)
        if key in seen:
            continue
        seen.add(key)
        unique.append(s)
    return unique


def _append_citations_footer(answer: str, sources: List[ChatResponseSource]) -> str:
    if not sources:
        return answer
    # Always include page references even if the LLM forgets to cite inline.
    citations = ", ".join(
        [f"{(s.source or 'PDF')} p.{s.pageNumber}" for s in sources[:8]]
    )
    return f"{answer.strip()}\n\nCitations: {citations}"


def _history_to_tuples(history: Optional[List[ChatTurn]]) -> List[Tuple[str, str]]:
    if not history:
        return []
    out: List[Tuple[str, str]] = []
    for t in history:
        role = (t.role or "").lower()
        if role in ("user", "human"):
            out.append(("human", t.content))
        elif role in ("assistant", "ai"):
            out.append(("ai", t.content))
    return out


def process_document_background(
    *,
    settings: Settings,
    document_id: str,
    session_id: str,
    file_path: str,
    original_filename: str,
) -> None:
    """
    Background ingestion:
      - Load PDF pages (PyPDFLoader)
      - Split into chunks with metadata: {"page": page, "source": filename}
      - Embed chunks with sentence-transformers
      - Store in MongoDB Atlas Vector Search collection
    """
    
    # CRITICAL: Apply keras patch BEFORE any embeddings/transformers imports
    # This is especially important for background tasks
    import sys
    import os
    os.environ['TF_USE_LEGACY_KERAS'] = '1'
    os.environ['KERAS_BACKEND'] = 'tensorflow'
    try:
        import tf_keras
        sys.modules['keras'] = tf_keras
        if hasattr(tf_keras, 'utils'):
            sys.modules['keras.utils'] = tf_keras.utils
        if hasattr(tf_keras, 'layers'):
            sys.modules['keras.layers'] = tf_keras.layers
        if hasattr(tf_keras, 'models'):
            sys.modules['keras.models'] = tf_keras.models
    except ImportError:
        pass

    client = get_mongo_client(settings)
    db = get_db(client, settings)
    documents = get_documents_collection(db, settings)
    chunks = get_chunks_collection(db, settings)
    ensure_non_vector_indexes(documents, chunks)

    try:
        pages = load_pdf_pages(file_path, source_filename=original_filename)
        if not pages:
            raise ValueError("No text could be extracted from this PDF.")

        split_chunks = split_into_chunks(
            pages, chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap
        )
        texts = [c.page_content for c in split_chunks]

        embeddings = get_embeddings(settings)
        vectors = embeddings.embed_documents(texts)

        if vectors and len(vectors[0]) != settings.embeddings_dimensions:
            raise ValueError(
                "Embedding dimensions mismatch. "
                f"Got {len(vectors[0])}, expected {settings.embeddings_dimensions}. "
                "Update EMBEDDINGS_DIMENSIONS and recreate the Atlas Vector Search index."
            )

        now = utc_now().isoformat()
        chunk_docs: List[Dict[str, Any]] = []
        for idx, (chunk, vec) in enumerate(zip(split_chunks, vectors)):
            meta = {
                "page": int(chunk.metadata.get("page")),
                "source": chunk.metadata.get("source"),
            }
            chunk_docs.append(
                {
                    "sessionId": session_id,
                    "documentId": document_id,
                    "text": chunk.page_content,
                    "embedding": vec,
                    "metadata": meta,  # required contract
                    "page": meta["page"],
                    "source": meta["source"],
                    "chunkIndex": idx,
                    "createdAt": now,
                }
            )

        inserted = insert_chunks(chunks, chunk_docs)
        if inserted == 0:
            raise ValueError("No chunks were stored (empty document).")

        update_document_status(
            documents,
            document_id=document_id,
            status="READY",
            pages=len(pages),
            error_message=None,
        )
    except Exception as e:  # pragma: no cover
        update_document_status(
            documents,
            document_id=document_id,
            status="ERROR",
            pages=0,
            error_message=str(e),
        )
    finally:
        try:
            Path(file_path).unlink(missing_ok=True)
        except Exception:
            pass
        client.close()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(title="DocuChat", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        return {"ok": True}

    # ---------------------------------------------------------------------
    # Required endpoints (per your spec)
    # ---------------------------------------------------------------------

    @app.post("/upload", response_model=UploadResponse)
    async def upload_pdf(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        session_id: Optional[str] = Form(None),
        x_session_id: Optional[str] = Header(None),
        settings: Settings = Depends(get_settings),
    ):
        _validate_upload(settings, file)

        session = _safe_session_id(settings, session_id or x_session_id)
        document_id = str(uuid.uuid4())

        client = get_mongo_client(settings)
        db = get_db(client, settings)
        documents = get_documents_collection(db, settings)
        chunks = get_chunks_collection(db, settings)
        ensure_non_vector_indexes(documents, chunks)

        record = create_document_record(
            documents,
            document_id=document_id,
            session_id=session,
            file_name=file.filename or f"{document_id}.pdf",
            file_size=None,
        )

        try:
            file_path = _save_upload_to_disk(settings, document_id, file)
        except Exception as e:
            update_document_status(
                documents,
                document_id=document_id,
                status="ERROR",
                error_message=f"Failed to store upload: {e}",
            )
            raise HTTPException(status_code=500, detail="Failed to store upload.") from e
        finally:
            client.close()

        background_tasks.add_task(
            process_document_background,
            settings=settings,
            document_id=document_id,
            session_id=session,
            file_path=file_path,
            original_filename=record["fileName"],
        )

        return UploadResponse(**record)

    @app.post("/chat", response_model=ChatResponse)
    async def chat(
        req: ChatRequest,
        settings: Settings = Depends(get_settings),
    ):
        session = _safe_session_id(settings, req.session_id)

        client = get_mongo_client(settings)
        db = get_db(client, settings)
        chunks = get_chunks_collection(db, settings)

        retriever = MongoAtlasVectorRetriever(
            chunks_collection=chunks,
            embeddings=get_embeddings(settings),
            index_name=settings.mongodb_vector_index_name,
            top_k=settings.top_k,
            num_candidates=settings.num_candidates,
            session_id=session,
            document_id=None,  # session-wide (multiple PDFs)
        )

        docs = retriever.get_relevant_documents(req.question)
        if not docs:
            return ChatResponse(
                answer=(
                    "I couldn't find relevant content in your uploaded PDFs for this session. "
                    "Try rephrasing your question or uploading a different PDF."
                ),
                sources=[],
            )

        # LangChain chain (satisfies: RetrievalQA or ConversationalRetrievalChain)
        from langchain.chains import ConversationalRetrievalChain, RetrievalQA  # type: ignore
        from langchain_core.prompts import ChatPromptTemplate  # type: ignore

        llm = get_llm(settings)

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are DocuChat, an AI assistant that answers questions about PDF documents.\n\n"
                    "Instructions:\n"
                    "- Answer the user's question using the provided context from the PDF.\n"
                    "- Synthesize information across multiple pages/chunks when relevant.\n"
                    "- If you have partial information, provide what you know and note if more details might be in other pages.\n"
                    "- Be helpful and comprehensive - don't just say 'insufficient information' if you can provide useful insights from what's available.\n"
                    "- Always include page references in your answer (e.g., 'According to [filename p.3]...').\n"
                    "- If the answer truly isn't in the context, say so clearly.",
                ),
                (
                    "human",
                    "CONTEXT FROM PDF:\n{context}\n\nQUESTION: {question}\n\n"
                    "Provide a comprehensive answer based on the context above. Include specific page references for all claims.",
                ),
            ]
        )

        # We already retrieved docs to build context + sources; still use a chain for the LLM step.
        context = _docs_to_prompt_context(docs)

        history = _history_to_tuples(req.chat_history)
        if history:
            chain = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=retriever,
                return_source_documents=True,
                combine_docs_chain_kwargs={"prompt": prompt},
            )
            out = chain({"question": req.question, "chat_history": history})
            answer = out.get("answer") or out.get("result") or ""
            used_docs = out.get("source_documents") or docs
        else:
            chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True,
                chain_type_kwargs={"prompt": prompt},
            )
            out = chain({"query": req.question})
            answer = out.get("result") or ""
            used_docs = out.get("source_documents") or docs

        sources = _compact_sources(used_docs)
        # Footer citations removed - sources still available in response
        client.close()
        return ChatResponse(answer=answer, sources=sources)

    # ---------------------------------------------------------------------
    # UI compatibility routes (existing React app expects these)
    # Base URL: http://localhost:8080/api
    # ---------------------------------------------------------------------

    @app.get("/api/documents")
    def ui_list_documents(
        x_session_id: Optional[str] = Header(None),
        settings: Settings = Depends(get_settings),
    ):
        session = _safe_session_id(settings, x_session_id)
        client = get_mongo_client(settings)
        db = get_db(client, settings)
        documents = get_documents_collection(db, settings)
        res = list_documents(documents, session_id=session)
        client.close()
        return res

    @app.post("/api/documents/upload", response_model=UploadResponse)
    async def ui_upload_document(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        x_session_id: Optional[str] = Header(None),
        settings: Settings = Depends(get_settings),
    ):
        # Proxy to required endpoint logic, but keep the response shape.
        return await upload_pdf(
            background_tasks=background_tasks,
            file=file,
            session_id=None,
            x_session_id=x_session_id,
            settings=settings,
        )

    @app.get("/api/documents/{document_id}")
    def ui_get_document(
        document_id: str,
        x_session_id: Optional[str] = Header(None),
        settings: Settings = Depends(get_settings),
    ):
        session = _safe_session_id(settings, x_session_id)
        client = get_mongo_client(settings)
        db = get_db(client, settings)
        documents = get_documents_collection(db, settings)
        doc = get_document(documents, document_id=document_id)
        client.close()
        if not doc or doc.get("sessionId") != session:
            raise HTTPException(status_code=404, detail="Document not found.")
        return doc

    @app.delete("/api/documents/{document_id}")
    def ui_delete_document(
        document_id: str,
        x_session_id: Optional[str] = Header(None),
        settings: Settings = Depends(get_settings),
    ):
        session = _safe_session_id(settings, x_session_id)
        client = get_mongo_client(settings)
        db = get_db(client, settings)
        documents = get_documents_collection(db, settings)
        chunks = get_chunks_collection(db, settings)
        delete_document_and_chunks(documents, chunks, document_id=document_id, session_id=session)
        client.close()
        return {"ok": True}

    @app.post("/api/chat/query", response_model=ChatResponse)
    async def ui_chat_query(
        req: UIChatQueryRequest,
        x_session_id: Optional[str] = Header(None),
        settings: Settings = Depends(get_settings),
    ):
        """
        UI expects chat scoped to a single selected document.
        """
        # #region agent log
        try:
            import json, sys, os
            with open('/Users/keshavghimire/AI/DocuChat/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"api.py:535","message":"ui_chat_query entry","data":{"python_executable":sys.executable,"document_id":req.documentId},"timestamp":int(__import__('time').time()*1000)}) + '\n')
        except Exception as e:
            try:
                with open('/Users/keshavghimire/AI/DocuChat/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"api.py:543","message":"Log write failed","data":{"error":str(e)},"timestamp":int(__import__('time').time()*1000)}) + '\n')
            except: pass
        # #endregion
        client = None
        try:
            session = _safe_session_id(settings, x_session_id)
            client = get_mongo_client(settings)
            db = get_db(client, settings)
            chunks = get_chunks_collection(db, settings)

            # #region agent log
            import json, sys
            try:
                with open('/Users/keshavghimire/AI/DocuChat/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"api.py:551","message":"Before get_embeddings call in chat","data":{"python_executable":sys.executable,"document_id":req.documentId},"timestamp":int(__import__('time').time()*1000)}) + '\n')
            except: pass
            # #endregion
            
            retriever = MongoAtlasVectorRetriever(
                chunks_collection=chunks,
                embeddings=get_embeddings(settings),
                index_name=settings.mongodb_vector_index_name,
                top_k=settings.top_k,
                num_candidates=settings.num_candidates,
                session_id=session,
                document_id=req.documentId,
            )
            
            # #region agent log
            try:
                with open('/Users/keshavghimire/AI/DocuChat/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"api.py:563","message":"After get_embeddings call in chat","data":{"success":True},"timestamp":int(__import__('time').time()*1000)}) + '\n')
            except: pass
            # #endregion

            # Check if document exists and has chunks
            from backend.vector_store import get_document, get_documents_collection
            documents = get_documents_collection(db, settings)
            doc = get_document(documents, document_id=req.documentId)
            
            if not doc:
                return ChatResponse(
                    answer="Document not found. Please upload the document first.",
                    sources=[],
                )
            
            if doc.get("status") != "READY":
                return ChatResponse(
                    answer=f"Document is still processing (status: {doc.get('status')}). Please wait and try again.",
                    sources=[],
                )
            
            # Check if chunks exist for this document
            chunk_count = chunks.count_documents({"documentId": req.documentId})
            if chunk_count == 0:
                return ChatResponse(
                    answer=(
                        "This document has no processed chunks yet. "
                        "The document may still be processing, or there was an error during ingestion. "
                        "Please try uploading the document again."
                    ),
                    sources=[],
                )
            
            docs = retriever.get_relevant_documents(req.question)
            if not docs:
                return ChatResponse(
                    answer=(
                        f"I couldn't find relevant content matching your question in this PDF. "
                        f"The document has {chunk_count} chunks, but none matched your query. "
                        "Try rephrasing your question with different keywords or asking about specific topics mentioned in the document."
                    ),
                    sources=[],
                )

            from langchain.chains import RetrievalQA  # type: ignore
            from langchain_core.prompts import ChatPromptTemplate  # type: ignore

            llm = get_llm(settings)
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are DocuChat.\n"
                        "Answer ONLY using the provided context.\n"
                        "You MUST include page references in the answer (e.g., [filename p.3]).",
                    ),
                    (
                        "human",
                        "CONTEXT:\n{context}\n\nQUESTION:\n{question}\n\n"
                        "Return a concise, helpful answer with citations.",
                    ),
                ]
            )

            # Use RetrievalQA as required by spec.
            chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True,
                chain_type_kwargs={"prompt": prompt},
            )
            out = chain({"query": req.question})
            answer = out.get("result") or ""
            used_docs = out.get("source_documents") or docs

            sources = _compact_sources(used_docs)
            return ChatResponse(answer=answer, sources=sources)
        except Exception as e:
            import traceback
            error_msg = str(e)
            # #region agent log
            try:
                import json, sys
                with open('/Users/keshavghimire/AI/DocuChat/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"api.py:637","message":"Chat query exception caught","data":{"error":error_msg,"error_type":type(e).__name__,"traceback":traceback.format_exc()},"timestamp":int(__import__('time').time()*1000)}) + '\n')
            except: pass
            # #endregion
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Error processing chat query: {error_msg}"
            )
        finally:
            if client:
                client.close()

    return app


app = create_app()


