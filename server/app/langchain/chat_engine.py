from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    AIMessageChunk,
    ToolMessage,
)
from app.schema.chatSchema import Context

from app.core.logging import logger
from app.langchain.llm import get_agent


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
    ) -> str:
        messages = ChatEngine.compose_chat_messages(history, prompt)
        agent = get_agent(llm_model)
        try:
            res = await agent.ainvoke(
                {"messages": messages}, context=Context(thread_id=thread_id)
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
    ):
        messages = ChatEngine.compose_chat_messages(history, prompt)
        agent = get_agent(llm_model)
        try:
            async for chunk, metadata in agent.astream(
                {"messages": messages},
                stream_mode="messages",
                context=Context(thread_id=thread_id),
            ):
                if isinstance(chunk, AIMessageChunk):
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
                        yield {
                            "type": "ai",
                            "content": chunk.content,
                        }

                elif isinstance(chunk, ToolMessage):
                    yield {
                        "type": "tool",
                        "tool": chunk.name,
                        "content": chunk.content,
                    }
        except Exception as e:
            logger.error("stream failed: %s", e, exc_info=True)
            raise RuntimeError("An error occurred while streaming the response.") from e
