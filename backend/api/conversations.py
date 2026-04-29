from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from agent.llm_model import get_title
from api.deps import get_current_active_user
from db.session import get_db
from models.user import Conversation, Message, User

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


class ConversationResponse(BaseModel):
    conversation_id: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime


class UpdateConversationRequest(BaseModel):
    description: str


class GenerateDescriptionRequest(BaseModel):
    first_message: str


def _conversation_to_response(conversation: Conversation) -> dict:
    return {
        "conversation_id": conversation.conversation_id,
        "description": conversation.description,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
    }


def _message_to_response(message: Message) -> dict:
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at,
    }


async def generate_conversation_description(first_message: str) -> Any:
    title = await get_title(first_message)
    return title


def _normalize_generated_description(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()

    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
        return " ".join(parts).strip()

    content = getattr(value, "content", None)
    if content is not None:
        return _normalize_generated_description(content)

    return str(value).strip()


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
    )
    return [_conversation_to_response(conversation) for conversation in result.scalars().all()]


@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    conversation = Conversation(
        conversation_id=str(uuid4()),
        user_id=current_user.id,
        description=None,
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return _conversation_to_response(conversation)


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    await _get_user_conversation(conversation_id, db, current_user)
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
    )
    return [_message_to_response(message) for message in result.scalars().all()]


async def _get_user_conversation(
    conversation_id: str,
    db: AsyncSession,
    current_user: User,
) -> Conversation:
    result = await db.execute(
        select(Conversation).where(
            Conversation.conversation_id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return conversation


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    req: UpdateConversationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    description = req.description.strip()
    if not description:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Description is required",
        )

    conversation = await _get_user_conversation(conversation_id, db, current_user)

    conversation.description = description[:500]
    conversation.updated_at = datetime.now()
    await db.commit()
    await db.refresh(conversation)
    return _conversation_to_response(conversation)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.conversation_id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        return

    await db.execute(delete(Message).where(Message.conversation_id == conversation_id))
    await db.delete(conversation)
    await db.commit()


@router.post("/{conversation_id}/description", response_model=ConversationResponse)
async def generate_and_update_conversation_description(
    conversation_id: str,
    req: GenerateDescriptionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    first_message = req.first_message.strip()
    if not first_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="First message is required",
        )

    conversation = await _get_user_conversation(conversation_id, db, current_user)
    generated_description = await generate_conversation_description(first_message)
    description = _normalize_generated_description(generated_description)
    if not description:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Description generation failed",
        )

    conversation.description = description[:500]
    conversation.updated_at = datetime.now()
    await db.commit()
    await db.refresh(conversation)
    return _conversation_to_response(conversation)
