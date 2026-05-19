"""State schema for the RAG LangGraph."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from langchain.schema import Document


class RagState(TypedDict, total=False):
    question: str
    chat_history: list
    research_mode: Literal['kb', 'web']
    standalone_question: str
    search_queries: list[str]
    documents: list[Document]
    answer: str
    message: str
    metadata: dict[str, Any]
