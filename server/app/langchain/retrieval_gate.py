"""
Adaptive Retrieval Gate
------------------------
Decides, before the agent's tool-calling loop runs, whether retrieval is
needed for a given query and — if so — how aggressively to retrieve.

This is a lightweight LLM-based router (few-shot prompted), not a trained
classifier. It returns a structured decision that downstream code (llm.py /
chat_engine.py / tools.py) uses to skip retrieval entirely or set top_k on the
retrieve_relevant_chunks tool.
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, ValidationError

from app.core.logging import logger
from app.langchain.basic_rag import BasicRAG


# --- Strategy constants -----------------------------------------------------

class RetrievalStrategy(str, Enum):
    NONE = "none"
    LIGHT = "light"
    HEAVY = "heavy"


TOP_K_BY_STRATEGY: dict[RetrievalStrategy, int] = {
    RetrievalStrategy.NONE: 0,
    RetrievalStrategy.LIGHT: 3,
    RetrievalStrategy.HEAVY: 10,
}

DEFAULT_STRATEGY = RetrievalStrategy.LIGHT  # fallback if the LLM call fails


# --- Structured output schema ------------------------------------------------

class RetrievalGateDecision(BaseModel):
    needs_retrieval: bool = Field(
        ..., description="Whether retrieval is needed to answer the query."
    )
    strategy: RetrievalStrategy = Field(
        ..., description="Retrieval depth: none, light (top_k=3), or heavy (top_k=10)."
    )
    reasoning: str = Field(
        ..., description="Brief (1-2 sentence) justification for the decision."
    )

    @property
    def top_k(self) -> int:
        return TOP_K_BY_STRATEGY[self.strategy]


# --- Few-shot prompt ----------------------------------------------------------

_SYSTEM_PROMPT = """You are a retrieval routing assistant for a RAG system.

Given a user's query and recent chat history, decide:
1. Whether retrieving documents/context is necessary to answer well.
2. If yes, how much to retrieve: "light" (a few chunks, for narrow/simple factual questions) or "heavy" (many chunks, for broad/complex/multi-part questions).
3. If retrieval would not help (e.g. greetings, opinions, math, or the answer is already in chat history), choose "none".

Respond ONLY with valid JSON matching this schema, no other text:
{"needs_retrieval": bool, "strategy": "none" | "light" | "heavy", "reasoning": "string"}

Examples:
Query: "hey, how are you?"
{"needs_retrieval": false, "strategy": "none", "reasoning": "Greeting, no factual content to retrieve."}

Query: "What does section 4.2 of the contract say about termination?"
{"needs_retrieval": true, "strategy": "light", "reasoning": "Narrow, specific lookup in a known document."}

Query: "Summarize all the risks and obligations across the uploaded documents."
{"needs_retrieval": true, "strategy": "heavy", "reasoning": "Broad, multi-part synthesis across many chunks."}

Query: "What's 12 * 7?"
{"needs_retrieval": false, "strategy": "none", "reasoning": "Pure computation, no retrieval needed."}
"""


def _format_history(chat_history: list[Any], max_turns: int = 4) -> str:
    """
    Render the last few turns of chat history as plain text for the prompt.
    """
    lines = []
    for msg in chat_history[-max_turns:]:
        if isinstance(msg, dict):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
        else:
            role = getattr(msg, "type", getattr(msg, "role", "unknown"))
            content = getattr(msg, "content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines) if lines else "(no prior history)"


def _safe_parse(raw_text: str) -> RetrievalGateDecision | None:
    """Attempt to parse the LLM's raw text output into a validated decision."""
    text = raw_text.strip()
    # Strip accidental markdown fences
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        data = json.loads(text)
        return RetrievalGateDecision(**data)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning("Retrieval gate: failed to parse LLM output (%s): %r", e, raw_text)
        return None


def classify_retrieval_need(
    query: str,
    chat_history: list[Any],
    llm: Any,
) -> RetrievalGateDecision:
    """
    Decide whether/how to retrieve for the given query.
    """
    history_text = _format_history(chat_history)
    user_prompt = f"Chat history:\n{history_text}\n\nQuery: {query}"

    try:
        response = llm.invoke(
            [
                SystemMessage(content=_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]
        )
        raw_text = getattr(response, "content", str(response))
    except Exception as e:
        logger.error("Retrieval gate: LLM call failed (%s). Falling back to default.", e)
        return RetrievalGateDecision(
            needs_retrieval=True,
            strategy=DEFAULT_STRATEGY,
            reasoning=f"Gate LLM call failed ({e}); defaulting to '{DEFAULT_STRATEGY.value}'.",
        )

    decision = _safe_parse(raw_text)
    if decision is None:
        return RetrievalGateDecision(
            needs_retrieval=True,
            strategy=DEFAULT_STRATEGY,
            reasoning=f"Gate output unparsable; defaulting to '{DEFAULT_STRATEGY.value}'.",
        )

    logger.info(
        "Retrieval gate decision: needs_retrieval=%s strategy=%s reasoning=%s",
        decision.needs_retrieval, decision.strategy, decision.reasoning,
    )
    return decision


class RetrievalGateRAG:
    """Adaptive Retrieval Gate Strategy: dynamically decides retrieval depth based on user query and history."""

    @staticmethod
    def retrieve_relevant_chunks(
        query: str,
        thread_id: str,
        top_k: int = 5,
        chat_history: list[Any] | None = None,
        llm_model: str | None = None,
    ) -> list[dict]:
        from app.langchain.llm import get_llm

        llm = get_llm(llm_model)
        decision = classify_retrieval_need(
            query=query,
            chat_history=chat_history or [],
            llm=llm,
        )

        if not decision.needs_retrieval or decision.strategy == RetrievalStrategy.NONE:
            logger.info("Retrieval gate skipped document retrieval for query: %s", query)
            return [
                {
                    "content": f"[Retrieval Gate Decision]: No document retrieval required ({decision.reasoning}).",
                    "source": "retrieval_gate",
                    "strategy": decision.strategy.value,
                    "reasoning": decision.reasoning,
                }
            ]

        gate_top_k = decision.top_k or top_k
        logger.info("Retrieval gate executing %s retrieval (top_k=%d)", decision.strategy.value, gate_top_k)
        return BasicRAG.retrieve_relevant_chunks(query=query, thread_id=thread_id, top_k=gate_top_k)