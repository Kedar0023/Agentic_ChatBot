from sqlalchemy.orm import Session

from app.models.chats import Message, MessageRole, MessageStatus


class MessageRepo:
    """Repository encapsulating all Message database operations."""

    @staticmethod
    def create(
        db: Session,
        thread_id: str,
        role: MessageRole,
        content: str,
        status: MessageStatus,
    ) -> Message:
        msg = Message(thread_id=thread_id, role=role, content=content, status=status)
        db.add(msg)
        return msg

    @staticmethod
    def get_by_thread(db: Session, thread_id: str) -> list[Message]:
        return (
            db.query(Message)
            .filter(Message.thread_id == thread_id)
            .order_by(Message.created_at)
            .all()
        )
