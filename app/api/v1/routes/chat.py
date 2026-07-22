import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.service.access_context_service import AccessContextService
from app.modules.chat.schemas import ChatMessageResponse, ConversationCreate, ConversationResponse, ConversationUpdate
from app.modules.chat.service.chat_service import ChatService
from app.modules.chat.service.conversation_service import ConversationService
from app.modules.users.models import User
from app.ai.exceptions import AIException

router = APIRouter()


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    schema: ConversationCreate,
    current_user: User = Depends(AccessContextService.get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Start a new chat conversation session."""
    service = ConversationService(db)
    conv = await service.create_conversation(current_user.id, schema)
    await db.commit()
    return conv


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
    messages = list(conv.messages)
    messages.sort(key=lambda m: m.created_at)
    return messages


@router.post("/conversations/{conversation_id}/messages", response_model=list[ChatMessageResponse])
async def send_message(
    conversation_id: uuid.UUID,
    user_message: str,
    current_user: User = Depends(AccessContextService.get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Send a user message to the AI chatbot and get a response."""
    chat_service = ChatService(db)
    try:
        await chat_service.get_response(user_id=current_user.id, conversation_id=conversation_id, user_message=user_message)
        await db.commit()
    except AIException as e:
        await db.rollback()
        err_msg = str(e)
        if "context" in err_msg.lower() or "token" in err_msg.lower():
            user_detail = "Layanan AI mengalami kelebihan batas konteks. Sistem telah menyederhanakan riwayat obrolan, silakan kirim ulang pesan Anda."
        else:
            user_detail = f"Kendala Layanan AI: {err_msg}"
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=user_detail
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Terjadi kesalahan sistem: {str(e)}"
        )

    # Retrieve all messages sorted by creation time
    conv_service = ConversationService(db)
    conv = await conv_service.get_conversation(conversation_id)
    if not conv or conv.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    messages = list(conv.messages)
    messages.sort(key=lambda m: m.created_at)
    return messages


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: uuid.UUID,
    schema: ConversationUpdate,
    current_user: User = Depends(AccessContextService.get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Update conversation fields like active_skill or title."""
    service = ConversationService(db)
    conv = await service.get_conversation(conversation_id)
    if not conv or conv.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    if schema.title is not None:
        conv.title = schema.title
    if schema.active_skill is not None:
        if schema.active_skill.lower() not in [None, "strategi", "visualisasi", "umum", ""]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Skill type not supported. Use 'strategi', 'visualisasi', or 'umum'."
            )
        
        target_skill = None if schema.active_skill.lower() in ["umum", ""] else schema.active_skill.lower()
        if conv.active_skill != target_skill:
            conv.active_skill = target_skill
            skill_labels = {
                None: "Umum 💬",
                "strategi": "Strategi 🧠",
                "visualisasi": "Visualisasi 📊"
            }
            label = skill_labels.get(target_skill, "Umum 💬")
            await service.add_message(conversation_id, "system", f"🔧 Mode Percakapan diubah ke: **Skill {label}**")

    db.add(conv)
    await db.commit()
    return conv


