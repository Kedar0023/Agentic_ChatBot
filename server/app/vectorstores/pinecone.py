from functools import lru_cache

from pinecone import Pinecone
from app.core.app_configs import getAppConfig

config = getAppConfig()


class PineconeVectorStore:
    def __init__(self):
        self.client = Pinecone(api_key=config.pinecone_api_key.get_secret_value())

        self.index = self.client.Index(config.pinecone_index.get_secret_value())

    def add_documents(
        self,
        *,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ):
        vectors = [
            {
                "id": ids[i],
                "values": embeddings[i],
                "metadata": {
                    **metadatas[i],
                    "document": documents[i],  # store chunk text
                },
            }
            for i in range(len(ids))
        ]

        return self.index.upsert(vectors=vectors)

    def similarity_search(
        self,
        *,
        embedding: list[float],
        top_k: int = 5,
        where: dict | None = None,
    ):
        return self.index.query(
            vector=embedding,
            top_k=top_k,
            filter=where,
            include_metadata=True,
        )

    def delete(
        self,
        *,
        ids: list[str] | None = None,
        where: dict | None = None,
    ):
        if ids:
            return self.index.delete(ids=ids)

        if where:
            return self.index.delete(filter=where)

        raise ValueError("Either ids or where must be provided.")


@lru_cache
def get_vector_store() -> PineconeVectorStore:
    return PineconeVectorStore()