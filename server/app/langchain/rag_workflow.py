from functools import lru_cache

from chromadb import QueryResult
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from app.vectorstores.chromadb import get_vector_store

@lru_cache
def get_embedding_model() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

#------------------------------------------------------------------------------------------

class RAGWorkflow:

    @staticmethod
    def thread_has_documents(thread_id: str) -> bool:
        vecStore = get_vector_store()
        collection = vecStore.collection
        results = collection.get(where={"thread_id": thread_id}, limit=1)
        return len(results["documents"]) > 0

    #---------------------------------------------------------------------------------------
    @staticmethod
    def load_pdf(pdf_path: str):
        loader = PyPDFLoader(pdf_path)
        return loader.load()

    @staticmethod
    def split_into_chunks(documents: list[Document]) -> list[Document]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=250,
            chunk_overlap=50,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        return splitter.split_documents(documents)
    #---------------------------------------------------------------------------------------

    @staticmethod
    def embed_chunks(chunks: list[Document]) -> list[list[float]]:
        model = get_embedding_model()
        texts = [chunk.page_content for chunk in chunks]
        return model.embed_documents(texts)

    @staticmethod
    def embed_query(query: str) -> list[float]:
        model = get_embedding_model()
        return model.embed_query(query)
    #---------------------------------------------------------------------------------------

    # NOTE : this below fn is just to format the res of vector store query to a more readable format
    @staticmethod
    def format_query_results(res: QueryResult) -> list[dict]:
        formatted_results = []
        if res and "documents" in res and res["documents"]:
            docs = res["documents"][0]
            metas = (
                res["metadatas"][0]
                if "metadatas" in res and res["metadatas"]
                else [{}] * len(docs)
            )
            distances = (
                res["distances"][0]
                if "distances" in res and res["distances"]
                else [None] * len(docs)
            )
            for doc_text, meta, dist in zip(docs, metas, distances):
                formatted_results.append({
                    "content": doc_text,
                    "filename": meta.get("filename"),
                    "page": meta.get("page"),
                    "distance": dist,
                })
        return formatted_results
    #---------------------------------------------------------------------------------------

    @staticmethod
    def retrieve_relevant_chunks(query: str, thread_id: str, top_k: int = 5) -> list[dict]:
        query_embedding = RAGWorkflow.embed_query(query)

        vecStore = get_vector_store()

        res = vecStore.similarity_search(
            embedding=query_embedding, top_k=top_k, where={"thread_id": thread_id}
        )
        formatted_res = RAGWorkflow.format_query_results(res)

        return formatted_res

    #---------------------------------------------------------------------------------------
