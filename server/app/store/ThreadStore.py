import uuid
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.chats import Thread
from app.models.document import Document, DocumentStatus


class ThreadStore:
    """Repository encapsulating all Thread database operations."""

    @staticmethod
    def create(db: Session, thread_id: uuid.UUID, user_id: int) -> Thread:
        thread = Thread(id=thread_id, user_id=user_id)
        db.add(thread)
        return thread

    @staticmethod
    def get_for_user(db: Session, thread_id: str, user_id: int) -> Thread | None:
        return db.query(Thread).filter(Thread.id == thread_id, Thread.user_id == user_id).first()

    @staticmethod
    def update_metadata(
        thread: Thread,
        title: str | None = None,
        llm_model: str | None = None,
        rag_strategy: str | None = None,
    ) -> None:
        if thread.title is None and title is not None:
            thread.title = title
        if thread.llm_model is None and llm_model is not None:
            thread.llm_model = llm_model
        if getattr(thread, "rag_strategy", None) is None and rag_strategy is not None:
            thread.rag_strategy = rag_strategy

    @staticmethod
    def update_model(thread: Thread, llm_model: str) -> None:
        thread.llm_model = llm_model

    @staticmethod
    def update_rag_strategy(thread: Thread, rag_strategy: str) -> None:
        thread.rag_strategy = rag_strategy

    @staticmethod
    def update_title(thread: Thread, title: str) -> None:
        thread.title = title

    @staticmethod
    def delete(db: Session, thread: Thread) -> None:
        db.delete(thread)


class DocStore:
    """Repository encapsulating all Document database operations."""

    @staticmethod
    # therad_id filename , s3_key ,content_type , file_size_bytes ,status
    def create(
        db: Session,
        id: UUID | None = None,
        thread_id: str = "",
        filename: str = "",
        s3_key: str = "",
        content_type: str = "",
        file_size_bytes: int = 0,
        status: DocumentStatus = DocumentStatus.PENDING,
    ) -> Document:
        kwargs = dict(
            thread_id=thread_id,
            filename=filename,
            s3_key=s3_key,
            content_type=content_type,
            file_size_bytes=file_size_bytes,
            status=status,
        )
        if id is not None:
            kwargs["id"] = id
        document = Document(**kwargs)
        db.add(document)
        return document

    @staticmethod
    def get_by_id(db: Session, document_id: str) -> Document | None:
        return db.query(Document).filter(Document.id == document_id).first()

    @staticmethod
    def get_by_id_and_thread(db: Session, document_id: str, thread_id: str) -> Document | None:
        return db.query(Document).filter(Document.id == document_id, Document.thread_id == thread_id).first()

    @staticmethod
    def get_all_by_thread(db: Session, thread_id: str) -> list[Document]:
        return db.query(Document).filter(Document.thread_id == thread_id).all()

    @staticmethod
    def delete(db: Session, document: Document) -> None:
        db.delete(document)

