from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.utils.prompts import SYSTEM_PROMPT

ollama_model = init_chat_model(model="qwen2.5:1.5b", model_provider="ollama", temperature=0.7)


class ChatEngine:
    """Static utility class wrapping all LLM interactions."""

    # this fn converts {role,content} to a LangChain AI/Human message
    @staticmethod
    def to_lc_message(role: str, content: str) -> HumanMessage | AIMessage:
        if role == "user":
            return HumanMessage(content=content)
        return AIMessage(content=content)

    # (system + history + new prompt)
    @staticmethod
    def compose_chat_messages(
        history: list[HumanMessage | AIMessage], prompt: str
    ) -> list[SystemMessage | HumanMessage | AIMessage]:
        return [
            SystemMessage(content=SYSTEM_PROMPT),
            *history,
            HumanMessage(content=prompt),
        ]

    @staticmethod
    async def invoke(history: list[HumanMessage | AIMessage], prompt: str) -> str:
        messages = ChatEngine.compose_chat_messages(history, prompt)
        res = await ollama_model.ainvoke(messages)
        return res.content

    @staticmethod
    async def stream(
        history: list[HumanMessage | AIMessage],
        prompt: str,
    ):
        messages = ChatEngine.compose_chat_messages(history, prompt)
        async for chunk in ollama_model.astream(messages):
            if chunk.content:
                yield chunk.content
