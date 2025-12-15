from __future__ import annotations

from backend.settings import Settings


def get_llm(settings: Settings):
    """
    Groq chat model via LangChain.
    """

    from langchain_groq import ChatGroq  # type: ignore

    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=settings.llm_temperature,
    )




