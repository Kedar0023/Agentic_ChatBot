import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base

if TYPE_CHECKING:
    from app.models.chats import Message


class MessageMetrics(Base):
    __tablename__ = "message_metrics"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    message_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("messages.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        unique=True,
    )

    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rag_strategy: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    message: Mapped["Message"] = relationship(
        "Message",
        back_populates="metrics",
    )
