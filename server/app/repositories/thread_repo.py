import uuid

from sqlalchemy.orm import Session

from app.models.chats import Thread


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
