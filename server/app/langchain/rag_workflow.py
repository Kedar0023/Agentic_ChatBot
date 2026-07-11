from functools import lru_cache

from langchain_community.document_loaders import PyPDFLoader 
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

@lru_cache
def get_embedding_model() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

class RAGWorkflow:

    @staticmethod
    def load_pdf(pdf_path: str):
        loader = PyPDFLoader(pdf_path)
        return loader.load()
    
    @staticmethod
    def split_into_chunks(documents: list[Document]) -> list[Document]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size= 1000,
            chunk_overlap= 100,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        return splitter.split_documents(documents)
    
    @staticmethod
    def embed_chunks(chunks: list[Document]) -> list[list[float]]:
        model = get_embedding_model()
        texts = [chunk.page_content for chunk in chunks]
        return model.embed_documents(texts)