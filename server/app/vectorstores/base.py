from abc import ABC, abstractmethod

class VectorStore(ABC):

    @abstractmethod
    def add_documents(self, documents):
        pass

    @abstractmethod
    def similarity_search(self, query, k=5):
        pass

    @abstractmethod
    def delete_documents(self, ids):
        pass