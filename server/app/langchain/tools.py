import re

from langchain.tools import ToolRuntime, tool
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import BaseTool

from app.langchain.basic_rag import BasicRAG
from app.langchain.workflow import RAGWorkflow
from app.types import Context


# ---------------------------------------------------------------------------------
@tool
def retrieve_relevant_chunks(query: str, runtime: ToolRuntime[Context], top_k: int = 5) -> list[dict]:
    """Search the user's uploaded document(s) for content relevant to their question.
    Only call this if the question likely requires info from the uploaded file(s)."""

    thread_id = runtime.context.thread_id
    if not RAGWorkflow.thread_has_documents(thread_id):
        return [{"error": "No documents found for this thread."}]

    rag_strategy = getattr(runtime.context, "rag_strategy", None) or "basic"
    llm_model = getattr(runtime.context, "llm_model", None)
    history = getattr(runtime.context, "history", None) or []

    if rag_strategy == "corrective":
        from app.langchain.corrective_retrieval import CorrectiveRAG

        return CorrectiveRAG.retrieve_relevant_chunks(
            query=query,
            thread_id=thread_id,
            top_k=top_k,
            llm_model=llm_model,
        )

    if rag_strategy == "adaptive_gate":
        from app.langchain.retrieval_gate import RetrievalGateRAG

        return RetrievalGateRAG.retrieve_relevant_chunks(
            query=query,
            thread_id=thread_id,
            top_k=top_k,
            chat_history=history,
            llm_model=llm_model,
        )

    return BasicRAG.retrieve_relevant_chunks(query=query, thread_id=thread_id, top_k=top_k)


# ---------------------------------------------------------------------------------

search = DuckDuckGoSearchRun()
# Compile regex with word boundaries (\b) to match whole words and ignore case
BLOCKED_TERMS = re.compile(
    r"\b(hack|exploit|bypass|ignore|jailbreak|override|inject|exfiltrate|"
    r"malware|ransomware|trojan|rootkit|keylogger|botnet|ddos|vulnerability|"
    r"payload|phishing|dox|crack)\b",
    re.IGNORECASE,
)


@tool
def guarded_search(query: str) -> str:
    """Search the web after applying a word-list safety guardrail."""
    if BLOCKED_TERMS.search(query):
        return "Query violated safety policy."

    result = search.invoke(query)

    if BLOCKED_TERMS.search(result):
        return "Result blocked by safety policy."

    return result


# ---------------------------------------------------------------------------------


def get_tools() -> list[BaseTool]:
    return [retrieve_relevant_chunks, guarded_search]
