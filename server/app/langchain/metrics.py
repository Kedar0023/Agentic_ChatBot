import time
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.messages.utils import count_tokens_approximately

from app.langchain.llm import AVAILABLE_MODELS, DEFAULT_MODEL


class MetricsCollector:
    """Collects token usage, latency, cost, and sources for a single RAG request."""

    def __init__(self, llm_model: str | None = None, rag_strategy: str | None = None):
        self.llm_model = llm_model or DEFAULT_MODEL
        self.rag_strategy = rag_strategy
        self.input_tokens: int = 0
        self.output_tokens: int = 0
        self.sources: list[dict[str, Any]] = []
        self._start_time: float = time.monotonic()
        self._end_time: float | None = None

    def record_tokens(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

    def estimate_tokens_from_messages(
        self,
        input_messages: list[BaseMessage],
        output_text: str = "",
    ) -> None:
        """Estimate tokens using LangChain's count_tokens_approximately if not already recorded."""
        if self.input_tokens == 0 and input_messages:
            try:
                self.input_tokens = count_tokens_approximately(input_messages)
            except Exception:
                self.input_tokens = 0

        if self.output_tokens == 0 and output_text:
            try:
                self.output_tokens = count_tokens_approximately([AIMessage(content=output_text)])
            except Exception:
                self.output_tokens = 0

    def add_source(self, filename: str | None, page: int | str | None, score: float | None = None) -> None:
        """Record a unique document source reference."""
        if not filename:
            return
        # Deduplicate
        for s in self.sources:
            if s.get("filename") == filename and s.get("page") == page:
                return
        self.sources.append({
            "filename": filename,
            "page": page,
            "score": score,
        })

    def stop(self) -> None:
        if self._end_time is None:
            self._end_time = time.monotonic()

    @property
    def latency_ms(self) -> int:
        end = self._end_time or time.monotonic()
        return max(0, int((end - self._start_time) * 1000))

    @property
    def cost_usd(self) -> float:
        model_data = AVAILABLE_MODELS.get(self.llm_model, {})
        cost_input = model_data.get("token_cost_per_1k_input", 0.0)
        cost_output = model_data.get("token_cost_per_1k_output", 0.0)
        total = (self.input_tokens / 1000.0) * cost_input + (self.output_tokens / 1000.0) * cost_output
        return round(total, 6)

    def to_dict(self) -> dict:
        return {
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "sources": self.sources,
            "metrics": {
                "latency_ms": self.latency_ms,
                "cost_usd": self.cost_usd,
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
            },
            "llm_model": self.llm_model,
            "rag_strategy": self.rag_strategy,
        }
