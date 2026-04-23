from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_active_user
from db.session import get_db
from models.user import Conversation, User

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


class ConversationResponse(BaseModel):
    conversation_id: str
    description: str | None
    created_at: datetime
    updated_at: datetime


def _conversation_to_response(conversation: Conversation) -> dict:
    return {
        "conversation_id": conversation.conversation_id,
        "description": conversation.description,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
    }


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
