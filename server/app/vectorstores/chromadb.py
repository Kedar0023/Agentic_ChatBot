from functools import lru_cache
from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection

from app.core.app_configs import getAppConfig

config = getAppConfig()

# NOTE : this is a wrapper on ChromaDB it only init persistent client & manage collection & CRUD opr
# to support other Vstores i decided to not add embedding_fn .
# need pre embedding


class ChromaVectorStore:
    def __init__(self):
        db_path = Path(config.chroma_persist_dir.get_secret_value()).expanduser()
        db_path.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(path=str(db_path))

        self.collection: Collection = self.client.get_or_create_collection(
            name=config.chroma_collection_name
        )

    def add_documents(
        self,
        *,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ):
        return self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def similarity_search(
        self,
        *,
        embedding: list[float],
        top_k: int = 5,
        where: dict | None = None,
    ):
        return self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=where,
        )

    def delete(
        self,
        *,
        ids: list[str] | None = None,
        where: dict | None = None,
    ):
        return self.collection.delete(
            ids=ids,
            where=where,
        )


@lru_cache
def get_vector_store() -> ChromaVectorStore:
    return ChromaVectorStore()
