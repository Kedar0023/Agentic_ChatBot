from langchain.tools import tool, ToolRuntime
import re

from app.langchain.rag_workflow import RAGWorkflow
from langchain_community.tools import DuckDuckGoSearchRun
from app.schema.chatSchema import Context
from langchain_core.tools import BaseTool


# ---------------------------------------------------------------------------------
@tool
def retrieve_relevant_chunks(
    query: str, runtime: ToolRuntime[Context], top_k: int = 5
) -> list[dict]:
    """Search the user's uploaded document(s) for content relevant to their question.
    Only call this if the question likely requires info from the uploaded file(s)."""

    thread_id = runtime.context.thread_id
    if not RAGWorkflow.thread_has_documents(thread_id):
        return [{"error": "No documents found for this thread."}]
    return RAGWorkflow.retrieve_relevant_chunks(query=query, thread_id=thread_id, top_k=top_k)

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
