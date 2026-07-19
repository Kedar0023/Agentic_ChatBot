from app.core.logging import logger
from functools import lru_cache

from tempfile import NamedTemporaryFile

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_voyageai import VoyageAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.vectorstores.pinecone import get_vector_store
from app.core.app_configs import getAppConfig

config = getAppConfig()

@lru_cache
def get_embedding_model() -> VoyageAIEmbeddings:
    return VoyageAIEmbeddings(
        model="voyage-4-lite",
        api_key=config.voyageai_api_key.get_secret_value(),
        output_dimension = 512
    )



# ------------------------------------------------------------------------------------------


# Embedding dimension must match VoyageAI output_dimension above
_EMBEDDING_DIM = 512


class RAGWorkflow:
    @staticmethod
    def thread_has_documents(thread_id: str) -> bool:
        """Check if any vectors exist for a given thread via a cheap zero-vector probe."""
        vec_store = get_vector_store()
        res = vec_store.similarity_search(
            embedding=[0.0] * _EMBEDDING_DIM,
            top_k=1,
            where={"thread_id": thread_id},
        )
        logger.info("Thread %s checked for document presence", thread_id)
        return len(res.get("matches", [])) > 0

    # ---------------------------------------------------------------------------------------
    # this fn loads bytes form r2 + construct a temp file & further workflow
    # The temporary file is automatically deleted after loading.
    @staticmethod
    def load_pdf_from_bytes(steam: bytes) -> list[Document]:
        with NamedTemporaryFile(suffix=".pdf", delete=True) as temp_file:
            temp_file.write(steam)
            temp_file.flush()

            loader = PyPDFLoader(temp_file.name)
            logger.info("PDF loaded from bytes")
            return loader.load()

    @staticmethod
    def split_into_chunks(documents: list[Document]) -> list[Document]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=250,
            chunk_overlap=50,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        logger.info("PDF split into chunks")
        return splitter.split_documents(documents)

    # ---------------------------------------------------------------------------------------

    @staticmethod
    def embed_chunks(chunks: list[Document]) -> list[list[float]]:
        model = get_embedding_model()
        texts = [chunk.page_content for chunk in chunks]
        logger.info("Embeddings of PDF chunks generated")
        return model.embed_documents(texts)

    @staticmethod
    def embed_query(query: str) -> list[float]:
        model = get_embedding_model()
        logger.info("Embeddings of query generated")
        return model.embed_query(query)

    # ---------------------------------------------------------------------------------------

    # NOTE : formats the Pinecone query response into a flat list of dicts
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

        vecStore = get_vector_store()

        res = vecStore.similarity_search(
            embedding=query_embedding, top_k=top_k, where={"thread_id": thread_id}
        )
        formatted_res = RAGWorkflow.format_query_results(res)
        return formatted_res

    # ---------------------------------------------------------------------------------------
