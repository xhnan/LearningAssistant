import json

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.auth import router as auth_router
from api.conversations import router as conversations_router
from api.deps import get_current_active_user
from agent.learning_agent import LearningAgentModel, stream_chat
from db.session import get_db
from models.user import Conversation, User
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI()

app.include_router(auth_router)
app.include_router(conversations_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    conversation_id: str
    messages: list[dict]


@app.get("/")
def root():
    return {"message": "LearningAssistant API is running"}


@app.post("/api/chat/stream")
async def chat_stream(
    req: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.conversation_id == req.conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    async def event_generator():
        try:
            agent_model = LearningAgentModel(
                messages=req.messages,
                thread_id=req.conversation_id,
                user_id=current_user.id,
            )
            async for token in stream_chat(agent_model):
                yield f"event: token\ndata: {json.dumps({'content': token})}\n\n"
            yield "event: done\ndata: {}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )



@app.get("/api/db/health")
async def db_health(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(text("select 1"))
    return {"ok": result.scalar_one() == 1}



