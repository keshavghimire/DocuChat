from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized, env-driven configuration.

    NOTE: MongoDB Atlas Vector Search index must be created manually in Atlas UI.
    We provide an index JSON in `backend/mongodb_vector_index.json`.
    """

    model_config = SettingsConfigDict(
        env_file=[".env", "backend/.env"],  # Try current dir, then backend dir
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # --- MongoDB ---
    mongodb_uri: str = Field(..., alias="MONGODB_URI")
    mongodb_db: str = Field("pdf_insight_chat", alias="MONGODB_DB")
    mongodb_documents_collection: str = Field("documents", alias="MONGODB_DOCUMENTS_COLLECTION")
    mongodb_chunks_collection: str = Field("chunks", alias="MONGODB_CHUNKS_COLLECTION")
    mongodb_vector_index_name: str = Field("chunks_vector_index", alias="MONGODB_VECTOR_INDEX_NAME")

    # --- LLM (Groq) ---
    groq_api_key: str = Field(..., alias="GROQ_API_KEY")
    groq_model: str = Field("llama3-70b-8192", alias="GROQ_MODEL")
    llm_temperature: float = Field(0.0, alias="LLM_TEMPERATURE")

    # --- Embeddings (Hugging Face sentence-transformers) ---
    embeddings_model_name: str = Field(
        "sentence-transformers/all-MiniLM-L6-v2", alias="EMBEDDINGS_MODEL_NAME"
    )

    # IMPORTANT: Atlas Vector Search index dimensions must match the embedding model.
    # all-MiniLM-L6-v2 -> 384
    embeddings_dimensions: int = Field(384, alias="EMBEDDINGS_DIMENSIONS")

    # --- Chunking ---
    chunk_size: int = Field(1000, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(150, alias="CHUNK_OVERLAP")

    # --- Retrieval ---
    top_k: int = Field(6, alias="TOP_K")
    num_candidates: int = Field(80, alias="NUM_CANDIDATES")

    # --- API/Server ---
    host: str = Field("0.0.0.0", alias="HOST")
    port: int = Field(8080, alias="PORT")
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        alias="CORS_ORIGINS",
    )

    storage_dir: str = Field("backend/storage", alias="STORAGE_DIR")
    max_upload_mb: int = Field(50, alias="MAX_UPLOAD_MB")

    # --- Session ---
    default_session_id: str = Field("default", alias="DEFAULT_SESSION_ID")

    def cors_origins_list(self) -> List[str]:
        """
        Support both JSON-ish list and comma-separated origins from env.
        """
        if isinstance(self.cors_origins, list):
            return self.cors_origins
        raw = str(self.cors_origins)
        return [o.strip() for o in raw.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


