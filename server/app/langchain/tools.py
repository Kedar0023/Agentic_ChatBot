from app.langchain.rag_workflow import RAGWorkflow
from langchain.tools import tool

#---------------------------------------------------------------------------------
@tool
def retrieve_relevant_chunks(query: str, thread_id: str, top_k: int = 5) -> list[dict]:
    """Search the user's uploaded document(s) for content relevant to their question.
    Only call this if the question likely requires info from the uploaded file(s)."""
    if not RAGWorkflow.thread_has_documents(thread_id):
        return [{"error": "No documents found for this thread."}]
    return RAGWorkflow.retrieve_relevant_chunks(query=query, thread_id=thread_id, top_k=top_k)


def get_tools() -> list:
    return [retrieve_relevant_chunks]