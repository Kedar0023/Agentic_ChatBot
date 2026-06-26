from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Enum as SQLEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.db import Base
from enum import Enum


# --------------------------------------------------------------------------------
class Thread(Base):
    __tablename__ = "threads"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # pyrefly: ignore [unknown-name]
    user: Mapped["User"] = relationship(  # noqa: F821
        back_populates="threads",
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="thread",
        cascade="all, delete-orphan",
    )

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    llm_model: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


# --------------------------------------------------------------------------------
class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# --------------------------------------------------------------------------------


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)

    thread_id: Mapped[int] = mapped_column(
        ForeignKey("threads.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    thread: Mapped["Thread"] = relationship(
        "Thread",
        back_populates="messages",
    )

    role: Mapped[MessageRole] = mapped_column(
        SQLEnum(MessageRole, name="message_role"),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
