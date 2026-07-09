import uuid

from sqlalchemy.orm import Session

from app.models.chats import Thread
from app.models.document import Document, DocumentStatus


class ThreadRepo:
    """Repository encapsulating all Thread database operations."""

    @staticmethod
    def create(db: Session, thread_id: uuid.UUID, user_id: int) -> Thread:
        thread = Thread(id=thread_id, user_id=user_id)
        db.add(thread)
        return thread

    @staticmethod
    def get_by_id_and_user(db: Session, thread_id: str, user_id: int) -> Thread | None:
        return db.query(Thread).filter(Thread.id == thread_id, Thread.user_id == user_id).first()

    @staticmethod
    def get_all_by_user(db: Session, user_id: int) -> list[Thread]:
        return (
            db.query(Thread)
            .filter(Thread.user_id == user_id)
            .order_by(Thread.updated_at.desc())
            .all()
        )

    @staticmethod
    def update_metadata(
        thread: Thread, title: str | None = None, llm_model: str | None = None
    ) -> None:
        """Set title / llm_model only when they have not been set yet."""
        if thread.title is None and title is not None:
            thread.title = title
        if thread.llm_model is None and llm_model is not None:
            thread.llm_model = llm_model


class DocumentRepo:
    """Repository encapsulating all Document database operations."""

    @staticmethod
    # therad_id filename , s3_key ,content_type , file_size_bytes ,status
    def create(
        db: Session,
        thread_id: str,
        filename: str,
        s3_key: str,
        content_type: str,
        file_size_bytes: int,
        status: DocumentStatus,
    ) -> None:
        document = Document(
            thread_id=thread_id,
            filename=filename,
            s3_key=s3_key,
            content_type=content_type,
            file_size_bytes=file_size_bytes,
            status=status,
        )
        db.add(document)
        return document


    @staticmethod
    def get_by_id(db: Session, document_id: str) -> Document | None:
        return db.query(Document).filter(Document.id == document_id).first()

    @staticmethod
    def get_by_id_and_thread(
        db: Session, document_id: str, thread_id: str
    ) -> Document | None:
        return (
            db.query(Document)
            .filter(Document.id == document_id, Document.thread_id == thread_id)
            .first()
        )
