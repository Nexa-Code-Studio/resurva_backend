import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChatMessageCreate(BaseModel):
    role: str  # "user", "assistant", "system", "tool"
    content: str


class ToolCallResponse(BaseModel):
    id: uuid.UUID
    chat_message_id: uuid.UUID
    tool_name: str
    tool_input: str | None
    tool_output: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatMessageResponse(ChatMessageCreate):
    id: uuid.UUID
    created_at: datetime
    tool_calls: list[ToolCallResponse] = []

    model_config = ConfigDict(from_attributes=True)



class ConversationCreate(BaseModel):
    store_id: uuid.UUID | None = None
    title: str | None = None


class ConversationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    store_id: uuid.UUID | None
    title: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
