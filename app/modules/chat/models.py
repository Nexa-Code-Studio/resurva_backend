import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, IdMixin, TimestampMixin

if TYPE_CHECKING:
    pass


class Conversation(Base, IdMixin, TimestampMixin):
    __tablename__ = "conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    store_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stores.id", ondelete="SET NULL"),
        nullable=True
    )
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    active_skill: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    messages: Mapped[list["ChatMessage"]] = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")


class ChatMessage(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "chat_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False
    )
    role: Mapped[str] = mapped_column(String, nullable=False)  # "user", "assistant", "system", "tool"
    content: Mapped[str] = mapped_column(String, nullable=False)

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
    tool_calls: Mapped[list["ToolCall"]] = relationship("ToolCall", back_populates="message", cascade="all, delete-orphan")


class ToolCall(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "chat_tool_calls"

    chat_message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        nullable=False
    )
    tool_name: Mapped[str] = mapped_column(String, nullable=False)
    tool_input: Mapped[str | None] = mapped_column(String, nullable=True)  # JSON String or raw text
    tool_output: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    message: Mapped["ChatMessage"] = relationship("ChatMessage", back_populates="tool_calls")


class ChatMemory(Base, IdMixin, TimestampMixin):
    __tablename__ = "chat_memories"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    value: Mapped[str] = mapped_column(String, nullable=False)
