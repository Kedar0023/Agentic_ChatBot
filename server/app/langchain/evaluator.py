import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.core.logging import logger
from app.langchain.llm import DEFAULT_MODEL, get_llm


class EvaluationOutput(BaseModel):
    quality: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall quality score between 0.0 and 1.0 based on coherence, clarity, and usefulness.",
    )
    quality_reason: str = Field(
        ...,
        description="Short reason for the quality score in 20 words or less.",
    )
    faithfulness: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Faithfulness score between 0.0 and 1.0 measuring whether statements are grounded in the provided sources.",
    )
    faithfulness_reason: str = Field(
        ...,
        description="Short reason for the faithfulness score in 20 words or less.",
    )


EVALUATOR_SYSTEM_PROMPT = """You are an objective AI evaluator assessing the quality and faithfulness of an answer produced by a RAG system.

EVALUATION CRITERIA:
1. "quality" (float from 0.0 to 1.0):
   - Measures how well-written, coherent, direct, and helpful the answer is.
   - 1.0 = Outstanding, clear, directly addresses the prompt.
   - 0.0 = Incoherent, unhelpful, or completely off-topic.
   - "quality_reason": Short reason in 20 words or less.

2. "faithfulness" (float from 0.0 to 1.0):
   - Measures whether the factual claims in the answer are strictly supported by the provided sources (no hallucinations).
   - 1.0 = Fully grounded in the provided sources.
   - Lower = Contains fabricated facts, unsupported claims, or contradictions of sources.
   - If no sources are provided, rate whether the answer appropriately acknowledges lack of context without claiming false information.
   - "faithfulness_reason": Short reason in 20 words or less.

OUTPUT FORMAT:
Respond ONLY with a valid JSON object matching this exact structure, with no markdown codeblocks, no formatting, and no commentary:
{"quality": 0.8, "quality_reason": "Direct, clear, and well-structured response.", "faithfulness": 0.9, "faithfulness_reason": "Claims are fully supported by the document chunks."}
"""


class RAGEvaluator:
    """Evaluates RAG answer quality and faithfulness using LLM-as-judge."""

    @staticmethod
    def _format_sources(sources: Any) -> str:
        if not sources:
            return "No sources provided."
        if isinstance(sources, str):
            return sources.strip()
        if isinstance(sources, list):
            formatted_chunks = []
            for idx, s in enumerate(sources):
                if isinstance(s, dict):
                    content = s.get("content") or s.get("text") or s.get("chunk") or ""
                    filename = s.get("filename") or "source"
                    page = s.get("page")
                    header = f"Source {idx + 1} ({filename}" + (f", page {page})" if page is not None else ")")
                    formatted_chunks.append(f"{header}:\n{content}" if content else header)
                else:
                    formatted_chunks.append(f"Source {idx + 1}: {s}")
            return "\n\n".join(formatted_chunks) if formatted_chunks else "No sources provided."
        return str(sources)

    @staticmethod
    def _parse_json_response(raw_text: str) -> dict[str, Any]:
        text = raw_text.strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
            text = text.strip()

        # Find first { and last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start : end + 1]

        data = json.loads(text)
        return EvaluationOutput(**data).model_dump()

    @classmethod
    async def aevaluate(
        cls,
        answer: str,
        sources: Any = None,
        query: str | None = None,
        llm_model: str | None = None,
    ) -> dict[str, Any]:
        """Asynchronously evaluate answer quality and faithfulness."""
        if not answer or not answer.strip():
            raise ValueError("Answer must be a non-empty string to evaluate.")

        formatted_sources = cls._format_sources(sources)
        user_prompt = f"Answer to evaluate:\n{answer}\n\nSources / Context:\n{formatted_sources}"
        if query:
            user_prompt = f"User Question:\n{query}\n\n" + user_prompt

        llm = get_llm(llm_model or DEFAULT_MODEL)
        messages = [
            SystemMessage(content=EVALUATOR_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        try:
            response = await llm.ainvoke(messages)
            raw_text = getattr(response, "content", str(response))
            output_dict = cls._parse_json_response(raw_text)

            # Ensure scores are clamped between 0.0 and 1.0
            quality_score = max(0.0, min(1.0, round(float(output_dict["quality"]), 2)))
            faithfulness_score = max(0.0, min(1.0, round(float(output_dict["faithfulness"]), 2)))

            return {
                "quality": quality_score,
                "quality_reason": output_dict["quality_reason"],
                "faithfulness": faithfulness_score,
                "faithfulness_reason": output_dict["faithfulness_reason"],
                "Short reason": f"Quality: {output_dict['quality_reason']} | Faithfulness: {output_dict['faithfulness_reason']}",
            }

        except Exception as e:
            logger.error("Failed to evaluate RAG response: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to evaluate response: {str(e)}") from e
