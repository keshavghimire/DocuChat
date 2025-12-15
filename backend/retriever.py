from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pymongo.collection import Collection

if TYPE_CHECKING:
    from backend.embeddings import EmbeddingsLike
else:
    EmbeddingsLike = Any


class MongoAtlasVectorRetriever(BaseRetriever):
    """
    Atlas Vector Search retriever using the native `$vectorSearch` stage.

    Why not rely purely on a VectorStore wrapper?
    - We need to reliably filter by `sessionId` and optionally `documentId`
    - We want to return similarity scores to the UI
    """

    chunks_collection: Collection
    embeddings: Any  # EmbeddingsLike protocol - using Any for Pydantic compatibility
    index_name: str
    top_k: int = 6
    num_candidates: int = 80
    session_id: str = "default"
    document_id: Optional[str] = None

    def _vector_search_pipeline(self, query_vector: List[float]) -> List[Dict[str, Any]]:
        filter_doc: Dict[str, Any] = {"sessionId": self.session_id}
        if self.document_id:
            filter_doc["documentId"] = self.document_id

        return [
            {
                "$vectorSearch": {
                    "index": self.index_name,
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": self.num_candidates,
                    "limit": self.top_k,
                    "filter": filter_doc,
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "text": 1,
                    "page": 1,
                    "source": 1,
                    "documentId": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        # #region agent log
        try:
            import json, sys
            with open('/Users/keshavghimire/AI/DocuChat/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"retriever.py:60","message":"Before embed_query call","data":{"keras_in_modules":"keras" in sys.modules},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                f.flush()
        except: pass
        # #endregion
        try:
            query_vector = self.embeddings.embed_query(query)
        except Exception as e:
            # #region agent log
            try:
                import traceback
                with open('/Users/keshavghimire/AI/DocuChat/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"retriever.py:67","message":"embed_query failed","data":{"error":str(e),"error_type":type(e).__name__,"traceback":traceback.format_exc()},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                    f.flush()
            except: pass
            # #endregion
            raise
        
        # Validate vector dimensions
        if len(query_vector) != 384:  # Should match EMBEDDINGS_DIMENSIONS
            raise ValueError(
                f"Query vector dimension mismatch: expected 384, got {len(query_vector)}"
            )

        # Atlas Vector Search expects the query vector length to match the index dimensions.
        try:
            results = list(
                self.chunks_collection.aggregate(self._vector_search_pipeline(query_vector))
            )
        except Exception as e:
            # Log the error but don't crash - return empty list
            import logging
            logging.error(f"Vector search error: {e}")
            return []

        docs: List[Document] = []
        for r in results:
            text = r.get("text", "")
            if not text:  # Skip empty chunks
                continue
            docs.append(
                Document(
                    page_content=text,
                    metadata={
                        "page": r.get("page"),
                        "source": r.get("source"),
                        "documentId": r.get("documentId"),
                        "similarity": r.get("score"),
                    },
                )
            )
        return docs


