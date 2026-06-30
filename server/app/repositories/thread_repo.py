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
        return (
            db.query(Thread)
            .filter(Thread.id == thread_id, Thread.user_id == user_id)
            .first()
        )
