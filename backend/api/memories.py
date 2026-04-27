from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_active_user
from db.session import get_db
from models.user import User
from models.memory import UserMemory

router = APIRouter(prefix="/api/memories", tags=["memories"])


class MemoryCreate(BaseModel):
    content: str
    memory_type: str
    source_message_id: int | None = None
    importance: float = 0.5


class MemoryUpdate(BaseModel):
    content: str | None = None
    memory_type: str | None = None
    importance: float | None = None
    is_active: bool | None = None


class MemoryResponse(BaseModel):
    id: int
    content: str
    memory_type: str
    source_message_id: int | None
    importance: float
    is_active: bool

    model_config = {"from_attributes": True}


class VectorSearchRequest(BaseModel):
    query_vector: list[float]
    top_k: int = 5


@router.post("", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(
    body: MemoryCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    memory = UserMemory(
        user_id=current_user.id,
        **body.model_dump(),
    )
    db.add(memory)
    await db.commit()
    await db.refresh(memory)
    return memory


@router.get("", response_model=list[MemoryResponse])
async def list_memories(
    memory_type: str | None = None,
    limit: int = Query(default=50, le=200),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(UserMemory)
        .where(UserMemory.user_id == current_user.id, UserMemory.is_active == True)
        .order_by(UserMemory.importance.desc(), UserMemory.updated_at.desc())
        .limit(limit)
    )
    if memory_type:
        stmt = stmt.where(UserMemory.memory_type == memory_type)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserMemory).where(
            UserMemory.id == memory_id, UserMemory.user_id == current_user.id
        )
    )
    memory = result.scalar_one_or_none()
    if memory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    return memory


@router.patch("/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    memory_id: int,
    body: MemoryUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserMemory).where(
            UserMemory.id == memory_id, UserMemory.user_id == current_user.id
        )
    )
    memory = result.scalar_one_or_none()
    if memory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(memory, field, value)

    await db.commit()
    await db.refresh(memory)
    return memory


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserMemory).where(
            UserMemory.id == memory_id, UserMemory.user_id == current_user.id
        )
    )
    memory = result.scalar_one_or_none()
    if memory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")

    memory.is_active = False
    await db.commit()


@router.post("/search", response_model=list[MemoryResponse])
async def vector_search(
    body: VectorSearchRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if len(body.query_vector) != 1536:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"query_vector must have 1536 dimensions, got {len(body.query_vector)}",
        )

    stmt = text(
        """
        SELECT id, content, memory_type, source_message_id, importance, is_active
        FROM user_memories
        WHERE user_id = :uid AND is_active = True AND embedding IS NOT NULL
        ORDER BY embedding <=> :query_vector
        LIMIT :top_k
        """
    )
    result = await db.execute(
        stmt,
        {
            "uid": current_user.id,
            "query_vector": str(body.query_vector).replace(" ", ""),
            "top_k": body.top_k,
        },
    )
    rows = result.fetchall()
    return [
        MemoryResponse(
            id=row[0],
            content=row[1],
            memory_type=row[2],
            source_message_id=row[3],
            importance=row[4],
            is_active=row[5],
        )
        for row in rows
    ]
