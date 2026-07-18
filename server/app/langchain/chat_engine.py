import logging

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    AIMessageChunk,
    ToolMessage,
)
from app.schema.chatSchema import Context

from app.langchain.tools import get_tools
from app.utils.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)
ollama_model = init_chat_model(model="qwen3:4b", model_provider="ollama", temperature=0.0)

agent_executor = create_agent(
    model=ollama_model, tools=get_tools(), system_prompt=SYSTEM_PROMPT, context_schema=Context
)

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
        history: list[HumanMessage | AIMessage], prompt: str, thread_id: str | None = None
    ) -> str:
        messages = ChatEngine.compose_chat_messages(history, prompt)
        try:
            res = await agent_executor.ainvoke(
                {"messages": messages}, context=Context(thread_id=thread_id)
            )
            return res["messages"][-1].content
        except Exception as e:
            logger.error("invoke failed: %s", e, exc_info=True)
            raise RuntimeError("Failed to generate a response from the language model.") from e

    # ---------------------------------------------------------------------------------------

    @staticmethod
    async def stream(
        history: list[HumanMessage | AIMessage], prompt: str, thread_id: str | None = None
    ):
        messages = ChatEngine.compose_chat_messages(history, prompt)
        # print(messages)
        try:
            async for chunk, metadata in agent_executor.astream(
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
