from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from backend.settings import Settings


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_mongo_client(settings: Settings) -> MongoClient:
    # MongoClient is thread-safe and intended to be long-lived.
    return MongoClient(settings.mongodb_uri)


def get_db(client: MongoClient, settings: Settings) -> Database:
    return client[settings.mongodb_db]


def get_documents_collection(db: Database, settings: Settings) -> Collection:
    return db[settings.mongodb_documents_collection]


def get_chunks_collection(db: Database, settings: Settings) -> Collection:
    return db[settings.mongodb_chunks_collection]


def ensure_non_vector_indexes(documents: Collection, chunks: Collection) -> None:
    """
    Create normal MongoDB indexes. Atlas Vector Search index is created separately.
    """
    documents.create_index("documentId", unique=True)
    documents.create_index([("sessionId", 1), ("createdAt", -1)])

    chunks.create_index([("sessionId", 1), ("documentId", 1)])
    chunks.create_index([("documentId", 1), ("page", 1)])


def create_document_record(
    documents: Collection,
    *,
    document_id: str,
    session_id: str,
    file_name: str,
    file_size: Optional[int],
) -> Dict[str, Any]:
    now = utc_now()
    doc = {
        "documentId": document_id,
        "sessionId": session_id,
        "fileName": file_name,
        "fileSize": file_size,
        "status": "PROCESSING",
        "pages": 0,
        "errorMessage": None,
        "createdAt": now.isoformat(),
        "updatedAt": now.isoformat(),
    }
    documents.insert_one(doc)
    return doc


def update_document_status(
    documents: Collection,
    *,
    document_id: str,
    status: str,
    pages: Optional[int] = None,
    error_message: Optional[str] = None,
) -> None:
    update: Dict[str, Any] = {"status": status, "updatedAt": utc_now().isoformat()}
    if pages is not None:
        update["pages"] = pages
    if error_message is not None:
        update["errorMessage"] = error_message

    documents.update_one({"documentId": document_id}, {"$set": update})


def get_document(documents: Collection, *, document_id: str) -> Optional[Dict[str, Any]]:
    return documents.find_one({"documentId": document_id}, {"_id": 0})


def list_documents(documents: Collection, *, session_id: str) -> List[Dict[str, Any]]:
    return list(
        documents.find({"sessionId": session_id}, {"_id": 0}).sort("createdAt", -1)
    )


def delete_document_and_chunks(
    documents: Collection, chunks: Collection, *, document_id: str, session_id: Optional[str] = None
) -> None:
    query = {"documentId": document_id}
    if session_id:
        query["sessionId"] = session_id

    documents.delete_one(query)
    chunks.delete_many({"documentId": document_id})


def insert_chunks(chunks: Collection, chunk_docs: Iterable[Dict[str, Any]]) -> int:
    chunk_docs_list = list(chunk_docs)
    if not chunk_docs_list:
        return 0
    res = chunks.insert_many(chunk_docs_list)
    return len(res.inserted_ids)




