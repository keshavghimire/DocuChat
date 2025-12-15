from __future__ import annotations

from pathlib import Path
from typing import List

from langchain_core.documents import Document


def load_pdf_pages(file_path: str, *, source_filename: str) -> List[Document]:
    """
    Load a PDF into one Document per page using LangChain's PyPDFLoader.

    Metadata contract (per your requirements):
      - metadata["page"]   : 1-indexed page number
      - metadata["source"] : original filename
    """

    from langchain_community.document_loaders import PyPDFLoader  # type: ignore

    path = Path(file_path)
    loader = PyPDFLoader(str(path))
    pages = loader.load()  # typically returns one Document per page with 0-indexed page metadata

    normalized: List[Document] = []
    for d in pages:
        page0 = d.metadata.get("page", 0)
        # Normalize to 1-indexed page number.
        page = int(page0) + 1
        normalized.append(
            Document(
                page_content=d.page_content,
                metadata={
                    "page": page,
                    "source": source_filename,
                },
            )
        )

    return normalized




