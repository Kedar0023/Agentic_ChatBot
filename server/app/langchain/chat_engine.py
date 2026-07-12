from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain.agents import create_agent

from app.utils.prompts import SYSTEM_PROMPT
from app.langchain.tools import get_tools

ollama_model = init_chat_model(model="qwen2.5:1.5b", model_provider="ollama", temperature=0.7)

agent_executor = create_agent(
    model=ollama_model,
    tools=get_tools(),
    system_prompt=SYSTEM_PROMPT,
)

#-----------------------------------------------------------------------------------------

#Static utility class wrapping all LLM interactions.
class ChatEngine:

    # this fn converts {role,content} to a LC AI/Human msg
    @staticmethod
    def to_lc_message(role: str, content: str) -> HumanMessage | AIMessage:
        if role == "user":
            return HumanMessage(content=content)
        return AIMessage(content=content)
    #---------------------------------------------------------------------------------------
    

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
    #---------------------------------------------------------------------------------------

    @staticmethod
    async def invoke(history: list[HumanMessage | AIMessage], prompt: str) -> str:
        messages = ChatEngine.compose_chat_messages(history, prompt)
        res = await agent_executor.ainvoke({"messages": messages})
        return res.content
    #---------------------------------------------------------------------------------------

    @staticmethod
    async def stream(
        history: list[HumanMessage | AIMessage],
        prompt: str,
    ):
        messages = ChatEngine.compose_chat_messages(history, prompt)
        print(messages)
        async for chunk,metadata in agent_executor.astream({"messages": messages},stream_mode="messages"):
            if chunk.content:
                yield chunk.content
