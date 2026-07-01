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
    def get_ordered_msgs_by_thread_id(db: Session, thread_id: str) -> list[Message]:
        return (
            db.query(Message)
            .filter(Message.thread_id == thread_id)
            .order_by(Message.created_at)
            .all()
        )

    @staticmethod
    def update_message(msg: Message, status: MessageStatus, content: str | None = None) -> None:
        msg.status = status
        if content is not None:
            msg.content = content
