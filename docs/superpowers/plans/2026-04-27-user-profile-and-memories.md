# User Profile & Long-term Memory Tables Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `user_profiles` and `user_memories` tables with SQLAlchemy models, Alembic migration, and CRUD APIs.

**Architecture:** Two new tables backed by PostgreSQL + pgvector. `UserProfile` is a one-to-one extension of `User` for structured data. `UserMemory` is a one-to-many table with a 1536-dim vector column for semantic retrieval. CRUD APIs expose read/write operations.

**Tech Stack:** SQLAlchemy 2.x async, pgvector, Alembic, FastAPI

---

### Task 1: Add pgvector dependency to requirements.txt

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add pgvector to requirements.txt**

In `backend/requirements.txt`, append a new line after `psycopg2-binary`:

```
pgvector>=0.3.0
```

Full file should be:

```
fastapi
uvicorn
langchain[google-genai]
python-dotenv
sqlalchemy
alembic
asyncpg
psycopg2-binary
pgvector>=0.3.0
bcrypt
python-jose[cryptography]
```

- [ ] **Step 2: Install the dependency**

Run: `pip install pgvector>=0.3.0`

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "feat: add pgvector dependency for vector column support"
```

---

### Task 2: Create UserProfile model

**Files:**
- Create: `backend/models/profile.py`
- Modify: `backend/models/user.py` (add relationship)

- [ ] **Step 1: Create `backend/models/profile.py`**

```python
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    learning_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    learning_goals: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_style: Mapped[str | None] = mapped_column(String(50), nullable=True)
    known_background: Mapped[str | None] = mapped_column(Text, nullable=True)
    constraints: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.now, onupdate=datetime.now
    )

    user: Mapped["User"] = relationship(back_populates="profile")
```

- [ ] **Step 2: Add profile relationship to User model**

In `backend/models/user.py`, add to the `User` class after the `conversations` relationship (line 21):

```python
    profile: Mapped["UserProfile | None"] = relationship(back_populates="user", uselist=False)
```

Also add the import at the top of `user.py` — but since it would create a circular import, use a TYPE_CHECKING guard:

```python
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base

if TYPE_CHECKING:
    from models.profile import UserProfile
```

Full `backend/models/user.py` after changes:

```python
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base

if TYPE_CHECKING:
    from models.profile import UserProfile


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="student")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now, onupdate=datetime.now)

    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    profile: Mapped["UserProfile | None"] = relationship(back_populates="user", uselist=False)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now, onupdate=datetime.now)

    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        {"comment": "用户聊天记录表"},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
        comment="消息ID",
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=False,
        comment="所属会话UUID",
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="消息角色: user/assistant/system",
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="消息内容",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.now,
        comment="创建时间",
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
```

- [ ] **Step 3: Commit**

```bash
git add backend/models/profile.py backend/models/user.py
git commit -m "feat: add UserProfile model with User relationship"
```

---

### Task 3: Create UserMemory model

**Files:**
- Create: `backend/models/memory.py`
- Modify: `backend/models/user.py` (add memories relationship)

- [ ] **Step 1: Create `backend/models/memory.py`**

```python
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class UserMemory(Base):
    __tablename__ = "user_memories"
    __table_args__ = (
        Index("ix_user_memories_user_active", "user_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    memory_type: Mapped[str] = mapped_column(String(50), nullable=False)
    embedding = mapped_column(Vector(1536), nullable=True)
    source_message_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    importance: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.now, onupdate=datetime.now
    )

    user: Mapped["User"] = relationship(back_populates="memories")
```

Note: `embedding` uses plain `mapped_column` (no `Mapped[]` type annotation) because `Vector` is a custom pgvector type, not a standard SQLAlchemy type with a Python-side type mapping.

- [ ] **Step 2: Add memories relationship to User model**

In `backend/models/user.py`, add to the `User` class after the `profile` relationship:

```python
    memories: Mapped[list["UserMemory"]] = relationship(back_populates="user", cascade="all, delete-orphan")
```

Also update the TYPE_CHECKING imports:

```python
if TYPE_CHECKING:
    from models.profile import UserProfile
    from models.memory import UserMemory
```

- [ ] **Step 3: Commit**

```bash
git add backend/models/memory.py backend/models/user.py
git commit -m "feat: add UserMemory model with pgvector embedding column"
```

---

### Task 4: Update Alembic env.py for new models and Vector type rendering

**Files:**
- Modify: `backend/alembic/env.py`

- [ ] **Step 1: Update `backend/alembic/env.py`**

Replace the entire file with:

```python
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from db.base import Base
from models.user import User, Conversation, Message
from models.profile import UserProfile
from models.memory import UserMemory

from alembic import context
from dotenv import load_dotenv
import os
from pgvector.sqlalchemy import Vector

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
load_dotenv()
database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise ValueError("DATABASE_URL is not set in the environment variables.")
# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata
if database_url:
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    config.set_main_option("sqlalchemy.url", database_url)

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def render_item(type_, obj, autogen_context):
    """Custom type renderer so Alembic can generate Vector(N) instead of unknown type."""
    if type_ == "type" and isinstance(obj, Vector):
        return f"Vector({obj.dim})"
    return False


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_item=render_item,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_item=render_item,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

Key changes:
- Import `UserProfile`, `UserMemory` so Alembic sees them in `Base.metadata`
- Import `Vector` from pgvector
- Add `render_item` function for Vector type rendering
- Pass `render_item=render_item` to `context.configure()` in both `run_migrations_offline` and `run_migrations_online`

- [ ] **Step 2: Commit**

```bash
git add backend/alembic/env.py
git commit -m "feat: register new models and pgvector render_item in Alembic env"
```

---

### Task 5: Generate and review Alembic migration

**Files:**
- Create: `backend/alembic/versions/<auto>_add_user_profiles_and_memories.py` (autogenerated)

- [ ] **Step 1: Generate migration**

Run:
```bash
cd backend
alembic revision --autogenerate -m "add user_profiles and user_memories tables"
```

- [ ] **Step 2: Review the generated migration**

Open the generated file and verify it contains:

**upgrade():**
1. `op.execute('CREATE EXTENSION IF NOT EXISTS vector')` — if not present, add it manually at the top of `upgrade()`
2. `op.create_table('user_profiles', ...)` with all columns and the FK to `users.id`
3. `op.create_table('user_memories', ...)` with all columns, FK to `users.id` and `messages.id`, and `Vector(1536)` for embedding
4. Index on `(user_id, is_active)`
5. No unexpected drops of existing indexes or tables

**downgrade():**
1. Drop `user_memories` table
2. Drop `user_profiles` table
3. No other changes

If autogenerate missed the `CREATE EXTENSION` statement, add this at the top of `upgrade()`:

```python
op.execute('CREATE EXTENSION IF NOT EXISTS vector')
```

And at the bottom of `downgrade()` (optional, usually you want to keep the extension):

```python
# Do NOT drop the vector extension in downgrade — other tables may use it
```

If the HNSW index for vector similarity search is not auto-generated, add it manually in `upgrade()` after the table creation:

```python
op.execute(
    "CREATE INDEX ix_user_memories_embedding ON user_memories "
    "USING hnsw (embedding vector_cosine_ops)"
)
```

And in `downgrade()` before dropping the table:

```python
op.drop_index("ix_user_memories_embedding", table_name="user_memories")
```

Also add at the top of the migration file:

```python
from pgvector.sqlalchemy import Vector
```

(This is needed so the `Vector(1536)` type reference in the migration works.)

- [ ] **Step 3: Apply migration**

Run:
```bash
cd backend
alembic upgrade head
```

Expected: No errors. Verify with `\dt` in psql that `user_profiles` and `user_memories` tables exist.

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat: add migration for user_profiles and user_memories tables"
```

---

### Task 6: Create profile CRUD API

**Files:**
- Create: `backend/api/profile.py`
- Modify: `backend/main.py` (register router)

- [ ] **Step 1: Create `backend/api/profile.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_active_user
from db.session import get_db
from models.user import User
from models.profile import UserProfile

router = APIRouter(prefix="/api/profile", tags=["profile"])


class ProfileUpdate(BaseModel):
    learning_level: str | None = None
    learning_goals: str | None = None
    preferred_style: str | None = None
    known_background: str | None = None
    constraints: str | None = None


class ProfileResponse(BaseModel):
    learning_level: str | None
    learning_goals: str | None
    preferred_style: str | None
    known_background: str | None
    constraints: str | None

    model_config = {"from_attributes": True}


@router.get("", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        return ProfileResponse(
            learning_level=None,
            learning_goals=None,
            preferred_style=None,
            known_background=None,
            constraints=None,
        )
    return profile


@router.put("", response_model=ProfileResponse)
async def upsert_profile(
    body: ProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        profile = UserProfile(user_id=current_user.id, **body.model_dump())
        db.add(profile)
    else:
        for field, value in body.model_dump().items():
            if value is not None:
                setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)
    return profile
```

- [ ] **Step 2: Register router in `backend/main.py`**

Add the import (after line 10):

```python
from api.profile import router as profile_router
```

Add the include (after line 21, after `app.include_router(conversations_router)`):

```python
app.include_router(profile_router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/api/profile.py backend/main.py
git commit -m "feat: add profile CRUD API with upsert"
```

---

### Task 7: Create memories CRUD API with vector search

**Files:**
- Create: `backend/api/memories.py`
- Modify: `backend/main.py` (register router)

- [ ] **Step 1: Create `backend/api/memories.py`**

```python
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
```

- [ ] **Step 2: Register router in `backend/main.py`**

Add the import:

```python
from api.memories import router as memories_router
```

Add the include:

```python
app.include_router(memories_router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/api/memories.py backend/main.py
git commit -m "feat: add memories CRUD API with vector similarity search"
```

---

## Self-Review

### Spec Coverage

| Spec Requirement | Task |
|---|---|
| pgvector dependency | Task 1 |
| UserProfile model with all columns | Task 2 |
| UserMemory model with Vector(1536) | Task 3 |
| User.profile relationship (one-to-one) | Task 2 |
| User.memories relationship (one-to-many) | Task 3 |
| Alembic env.py: new model imports | Task 4 |
| Alembic env.py: render_item for Vector type | Task 4 |
| Alembic env.py: render_item in both online/offline | Task 4 |
| Migration: CREATE EXTENSION vector | Task 5 |
| Migration: both tables with correct FK/cascade | Task 5 |
| Migration: composite index (user_id, is_active) | Task 5 |
| Migration: HNSW index on embedding | Task 5 |
| user_id ondelete CASCADE | Task 2, Task 3 |
| source_message_id ondelete SET NULL | Task 3 |
| Profile CRUD API | Task 6 |
| Memories CRUD API | Task 7 |
| Vector similarity search endpoint | Task 7 |
| embedding IS NOT NULL in vector search | Task 7 |

### Placeholder Scan

No TBD/TODO/placeholders found. All steps contain complete code.

### Type Consistency

- `UserProfile` fields match between model (Task 2) and API schemas (Task 6)
- `UserMemory` fields match between model (Task 3) and API schemas (Task 7)
- FK column names and table names consistent across all tasks
- Vector dimension 1536 consistent across model, migration, and search endpoint validation
