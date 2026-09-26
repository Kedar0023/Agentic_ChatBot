from app.core.logging import logger
from app.langchain.workflow import RAGWorkflow
from app.vectorstores.pinecone import get_vector_store


class BasicRAG:
    # NOTE: formats the Pinecone query response into a flat list of dicts
    @staticmethod
    def format_query_results(res: dict) -> list[dict]:
        formatted_results = []
        for match in res.get("matches", []):
            meta = match.get("metadata", {})
            formatted_results.append(
                {
                    "content": meta.get("document", ""),
                    "filename": meta.get("filename"),
                    "page": meta.get("page"),
                    "score": match.get("score"),
                }
            )
        logger.info("Pinecone query response formatted")
        return formatted_results

    # ---------------------------------------------------------------------------------------

    @staticmethod
    def retrieve_relevant_chunks(query: str, thread_id: str, top_k: int = 5) -> list[dict]:
        query_embedding = RAGWorkflow.embed_query(query)

        vec_store = get_vector_store()

        res = vec_store.similarity_search(
            embedding=query_embedding,
            top_k=top_k,
            where={"thread_id": thread_id},
        )
        formatted_res = BasicRAG.format_query_results(res)
        return formatted_res
