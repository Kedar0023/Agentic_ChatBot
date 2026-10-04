from typing import Any

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from app.core.logging import logger
from app.langchain.llm import get_agent
from app.types import Context

# -----------------------------------------------------------------------------------------


# Static utility class wrapping all LLM interactions.
class ChatEngine:
    # this fn converts {role,content} to a LC AI/Human msg
    @staticmethod
    def to_lc_message(role: str, content: str) -> HumanMessage | AIMessage:
        if role == "user":
            return HumanMessage(content=content)
        return AIMessage(content=content)

    # ---------------------------------------------------------------------------------------

    # (system + history + new prompt)
    @staticmethod
    def compose_chat_messages(
        history: list[HumanMessage | AIMessage], prompt: str
    ) -> list[SystemMessage | HumanMessage | AIMessage]:
        return [
            # SystemMessage(content=SYSTEM_PROMPT),
            *history,
            HumanMessage(content=prompt),
        ]

    # ---------------------------------------------------------------------------------------

    @staticmethod
    async def invoke(
        history: list[HumanMessage | AIMessage],
        prompt: str,
        thread_id: str | None = None,
        llm_model: str | None = None,
        rag_strategy: str | None = None,
    ) -> str:
        messages = ChatEngine.compose_chat_messages(history, prompt)
        agent = get_agent(llm_model)
        try:
            res = await agent.ainvoke(
                {"messages": messages},
                context=Context(
                    thread_id=thread_id or "",
                    rag_strategy=rag_strategy,
                    llm_model=llm_model,
                    history=history,
                ),
            )
            return res["messages"][-1].content
        except Exception as e:
            logger.error("invoke failed: %s", e, exc_info=True)
            raise RuntimeError("Failed to generate a response from the language model.") from e

    # ---------------------------------------------------------------------------------------

    @staticmethod
    async def stream(
        history: list[HumanMessage | AIMessage],
        prompt: str,
        thread_id: str | None = None,
        llm_model: str | None = None,
        rag_strategy: str | None = None,
        metrics_collector: Any | None = None,
    ):
        import json

        messages = ChatEngine.compose_chat_messages(history, prompt)
        agent = get_agent(llm_model)
        total_input_tokens = 0
        total_output_tokens = 0
        accumulated_text: list[str] = []

        try:
            async for chunk, metadata in agent.astream(
                {"messages": messages},
                stream_mode="messages",
                context=Context(
                    thread_id=thread_id or "",
                    rag_strategy=rag_strategy,
                    llm_model=llm_model,
                    history=history,
                ),
            ):
                if isinstance(chunk, AIMessageChunk):
                    # Track usage_metadata from provider if provided
                    if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                        total_input_tokens += chunk.usage_metadata.get("input_tokens", 0)
                        total_output_tokens += chunk.usage_metadata.get("output_tokens", 0)

                    # Tool invocation request from the LLM
                    if chunk.tool_calls:
                        for tc in chunk.tool_calls:
                            yield {
                                "type": "tool_call",
                                "tool": tc["name"],
                                "args": tc["args"],
                            }
                    # Streamed text content
                    elif chunk.content:
                        accumulated_text.append(str(chunk.content))
                        yield {
                            "type": "ai",
                            "content": chunk.content,
                        }

                elif isinstance(chunk, ToolMessage):
                    # Extract sources from retrieval tool output if collector provided
                    if metrics_collector and chunk.name == "retrieve_relevant_chunks":
                        try:
                            raw = chunk.content
                            data = json.loads(raw) if isinstance(raw, str) else raw
                            if isinstance(data, list):
                                for item in data:
                                    if isinstance(item, dict) and item.get("filename"):
                                        metrics_collector.add_source(
                                            filename=item.get("filename"),
                                            page=item.get("page"),
                                            score=item.get("score"),
                                        )
                        except Exception:
                            pass

                    yield {
                        "type": "tool",
                        "tool": chunk.name,
                        "content": chunk.content,
                    }
        except Exception as e:
            logger.error("stream failed: %s", e, exc_info=True)
            raise RuntimeError("An error occurred while streaming the response.") from e
        finally:
            if metrics_collector is not None:
                if total_input_tokens > 0 or total_output_tokens > 0:
                    metrics_collector.record_tokens(total_input_tokens, total_output_tokens)
                # Fallback to count_tokens_approximately if provider didn't return usage
                metrics_collector.estimate_tokens_from_messages(
                    input_messages=messages,
                    output_text="".join(accumulated_text),
                )
                metrics_collector.stop()
