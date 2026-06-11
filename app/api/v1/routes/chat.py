import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.service.access_context_service import AccessContextService
from app.modules.chat.schemas import ChatMessageResponse, ConversationCreate, ConversationResponse
from app.modules.chat.service.chat_service import ChatService
from app.modules.chat.service.conversation_service import ConversationService
from app.modules.users.models import User

router = APIRouter()


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    schema: ConversationCreate,
    current_user: User = Depends(AccessContextService.get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Start a new chat conversation session."""
    service = ConversationService(db)
    return await service.create_conversation(current_user.id, schema)


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(AccessContextService.get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Retrieve all conversations for the authenticated user."""
    service = ConversationService(db)
    return await service.get_user_conversations(current_user.id)


@router.get("/conversations/{conversation_id}/messages", response_model=list[ChatMessageResponse])
async def get_messages(
    conversation_id: uuid.UUID,
    current_user: User = Depends(AccessContextService.get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get all messages in a specific conversation."""
    service = ConversationService(db)
    conv = await service.get_conversation(conversation_id)
    if not conv or conv.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    return conv.messages


@router.post("/conversations/{conversation_id}/messages", response_model=str)
async def send_message(
    conversation_id: uuid.UUID,
    user_message: str,
    current_user: User = Depends(AccessContextService.get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Send a user message to the AI chatbot and get a response."""
    service = ChatService(db)
    return await service.get_response(user_id=current_user.id, conversation_id=conversation_id, user_message=user_message)
