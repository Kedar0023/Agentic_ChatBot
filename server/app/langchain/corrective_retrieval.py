"""Corrective retrieval: grade BasicRAG results and make at most one fallback attempt."""

from __future__ import annotations

import json
from enum import Enum
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.core.logging import logger
from app.langchain.basic_rag import BasicRAG
from app.langchain.tools import guarded_search

DEFAULT_RELEVANCE_THRESHOLD = 0.5


class RelevanceLabel(str, Enum):
    RELEVANT = "relevant"
    PARTIALLY_RELEVANT = "partially_relevant"
    IRRELEVANT = "irrelevant"


class ChunkRelevance(BaseModel):
    index: int = Field(..., ge=0)
    relevance: RelevanceLabel
    reason: str = Field(..., min_length=1)


class RelevanceGrade(BaseModel):
    grades: list[ChunkRelevance]


class QueryRewrite(BaseModel):
    query: str = Field(..., min_length=1)


GRADE_PROMPT = """Grade every retrieved chunk against the user's query.
Use exactly one label per chunk:
relevant = directly useful; partially_relevant = related but incomplete;
irrelevant = not useful. Return structured output only matching schema:
{"grades": [{"index": int, "relevance": "relevant"|"partially_relevant"|"irrelevant", "reason": "string"}]}"""

REWRITE_PROMPT = """Rewrite this query for a single fallback web search.
Preserve the user's intent and remove ambiguity. Return structured output matching schema:
{"query": "improved search query string"}"""


def _structured_invoke(llm: Any, schema: type[BaseModel], messages: list) -> BaseModel:
    """Invokes LLM with structured output, falling back to JSON text parsing if needed."""
    try:
        structured_llm = llm.with_structured_output(schema)
        res = structured_llm.invoke(messages)
        if isinstance(res, schema):
            return res
        if isinstance(res, dict):
            return schema(**res)
    except Exception as exc:
        logger.warning("with_structured_output failed (%s); attempting fallback JSON parsing", exc)

    # Fallback to direct invocation and JSON parsing
    resp = llm.invoke(messages)
    raw_text = getattr(resp, "content", str(resp)).strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.lower().startswith("json"):
            raw_text = raw_text[4:].strip()
    data = json.loads(raw_text)
    return schema(**data)


def _score(label: RelevanceLabel) -> float:
    return {
        RelevanceLabel.RELEVANT: 1.0,
        RelevanceLabel.PARTIALLY_RELEVANT: 0.5,
        RelevanceLabel.IRRELEVANT: 0.0,
    }[label]


def grade_and_correct(
    query: str,
    retrieved_docs: list,
    llm: Any,
    threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
) -> dict:
    """Grade BasicRAG output and perform at most one guarded-web fallback."""
    docs = [d for d in retrieved_docs if isinstance(d, dict) and not d.get("error")]
    if not docs:
        # Fallback to web search if no local docs were found
        logger.info("No documents found in store, attempting guarded web fallback")
        search_result = guarded_search.invoke({"query": query})
        return {
            "documents": [
                {
                    "content": search_result,
                    "filename": None,
                    "page": None,
                    "score": None,
                    "source": "guarded_search_fallback",
                    "query": query,
                }
            ],
            "correction_triggered": True,
            "correction_type": "web_search",
            "relevance_scores": [],
            "average_relevance": 0.0,
            "reason": "No local documents found; fallback web search triggered.",
        }

    chunks = "\n\n".join(
        f"CHUNK {i}:\n{doc.get('content', '')}" for i, doc in enumerate(docs)
    )
    try:
        grade = _structured_invoke(
            llm,
            RelevanceGrade,
            [
                SystemMessage(content=GRADE_PROMPT),
                HumanMessage(content=f"Query:\n{query}\n\n{chunks}"),
            ],
        )
    except Exception as exc:
        logger.warning("Corrective retrieval grading failed: %s", exc)
        return {
            "documents": retrieved_docs,
            "correction_triggered": False,
            "correction_type": None,
            "relevance_scores": [],
            "average_relevance": None,
            "reason": f"Grading failed: {exc}",
        }

    valid = [g for g in grade.grades if 0 <= g.index < len(docs)]
    relevance_scores = [
        {"index": g.index, "label": g.relevance.value, "reason": g.reason}
        for g in valid
    ]
    average = sum(_score(g.relevance) for g in valid) / len(docs) if valid else 0.0

    if average >= threshold:
        return {
            "documents": retrieved_docs,
            "correction_triggered": False,
            "correction_type": None,
            "relevance_scores": relevance_scores,
            "average_relevance": average,
            "reason": f"Average relevance {average:.3f} meets threshold {threshold:.3f}.",
        }

    # One correction only: rewrite, then one guarded search.
    corrected_query = query
    try:
        rewrite = _structured_invoke(
            llm,
            QueryRewrite,
            [
                SystemMessage(content=REWRITE_PROMPT),
                HumanMessage(content=query),
            ],
        )
        corrected_query = rewrite.query
    except Exception as exc:
        logger.warning("Query rewrite failed; using original query: %s", exc)

    search_result = guarded_search.invoke({"query": corrected_query})
    return {
        "documents": [
            *retrieved_docs,
            {
                "content": search_result,
                "filename": None,
                "page": None,
                "score": None,
                "source": "guarded_search",
                "query": corrected_query,
            },
        ],
        "correction_triggered": True,
        "correction_type": "web_search",
        "relevance_scores": relevance_scores,
        "average_relevance": average,
        "reason": (
            f"Average relevance {average:.3f} < threshold {threshold:.3f}; "
            "performed one guarded web-search correction."
        ),
    }


class CorrectiveRAG:
    """Corrective RAG Strategy: retrieves from vector store, evaluates relevance, and performs web fallback if needed."""

    @staticmethod
    def retrieve_relevant_chunks(
        query: str,
        thread_id: str,
        top_k: int = 5,
        llm_model: str | None = None,
        threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
    ) -> list[dict]:
        from app.langchain.llm import get_llm

        retrieved_docs = BasicRAG.retrieve_relevant_chunks(query=query, thread_id=thread_id, top_k=top_k)

        llm = get_llm(llm_model)
        corrected = grade_and_correct(
            query=query,
            retrieved_docs=retrieved_docs,
            llm=llm,
            threshold=threshold,
        )
        return corrected.get("documents", retrieved_docs)
