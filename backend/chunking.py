from __future__ import annotations

from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_into_chunks(
    pages: List[Document],
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> List[Document]:
    """
    Split page Documents into smaller chunks while preserving page/source metadata.
    """

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )

    # This preserves each Document's metadata on the resulting chunks.
    chunks = splitter.split_documents(pages)
    return chunks




