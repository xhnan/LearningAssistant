# User Profile & Long-term Memory Tables Design

## Goal

Add two tables to support AI long-term memory for the learning assistant:

1. **user_profiles** — structured, stable user profile (small data, full load into prompt)
2. **user_memories** — searchable long-term memories with vector recall via pgvector

## Tech Stack

- PostgreSQL + pgvector extension
- SQLAlchemy 2.x async ORM
- Alembic migrations
- Vector dimension: 1536

## Table: user_profiles

One-to-one with `users`, stores stable user attributes extracted by AI from conversations.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, autoincrement | Primary key |
| user_id | Integer | FK → users.id, unique, not null | Owning user |
| learning_level | String(50) | nullable | e.g. "beginner", "intermediate" |
| learning_goals | Text | nullable | Free-text learning objectives |
| preferred_style | String(50) | nullable | e.g. "example-driven", "formula-based" |
| known_background | Text | nullable | Prior knowledge description |
| constraints | Text | nullable | e.g. "30 min/day" |
| updated_at | DateTime(tz) | default now, onupdate now | Last update timestamp |

Usage: Full-load into system prompt every conversation turn. No vector search needed.

## Table: user_memories

One-to-many with `users`, stores retrievable long-term memories with embeddings.

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, autoincrement | Primary key |
| user_id | Integer | FK → users.id, not null | Owning user |
| content | Text | not null | Memory text content |
| memory_type | String(50) | not null | Type tag: "preference", "knowledge", "mistake", etc. |
| embedding | Vector(1536) | nullable | pgvector embedding (1536 dims). Nullable because embedding may be generated asynchronously after memory creation. Memories without embedding cannot participate in vector search and must use list/filter queries instead. |
| source_message_id | Integer | FK → messages.id, nullable | Origin message for traceability |
| importance | Float | default 0.5 | Importance score 0~1 |
| is_active | Boolean | default True | Soft delete flag |
| created_at | DateTime(tz) | default now | Creation time |
| updated_at | DateTime(tz) | default now, onupdate now | Last update time |

### Indexes

- `(user_id, is_active)` composite B-tree — filter active memories by user
- `embedding` HNSW index (cosine distance) — vector similarity search

### Retrieval

**Vector similarity search** (only memories with embedding):

```sql
SELECT content, importance
FROM user_memories
WHERE user_id = :uid AND is_active = True AND embedding IS NOT NULL
ORDER BY embedding <=> :query_vector
LIMIT :top_k;
```

**List/filter query** (all memories, including those without embedding):

```sql
SELECT content, importance, memory_type
FROM user_memories
WHERE user_id = :uid AND is_active = True
ORDER BY importance DESC, updated_at DESC
LIMIT :limit;
```

## File Organization

- Models: `backend/models/profile.py` (UserProfile), `backend/models/memory.py` (UserMemory)
- Migrations: New Alembic migration for both tables + pgvector extension
- APIs: `backend/api/profile.py` (CRUD), `backend/api/memories.py` (CRUD + vector search endpoint)

## Scope Boundaries

- This spec covers: table definitions, SQLAlchemy models, Alembic migration, basic CRUD APIs
- Out of scope: embedding generation logic, AI extraction logic, agent integration (user handles LLM parts)
