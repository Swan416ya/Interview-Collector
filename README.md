# Interview Collector

Monorepo for interview question collection and training.

## Swagger / API Docs

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Structure

- `backend`: FastAPI service
- `frontend`: Vue3 + Vite app
- `docs`: design docs

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

### Database Migration (Alembic)

1. 先在 MySQL 里创建数据库（只建库，不用建表）：

```sql
CREATE DATABASE interviewCollector CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

1. 生成并执行迁移：

```bash
cd backend
.\.venv\Scripts\activate
alembic revision --autogenerate -m "init tables"
alembic upgrade head
```

1. 启动后端：

```bash
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Verify

Backend:

```bash
http://localhost:8000/health
http://localhost:8000/docs
```

Frontend:

```bash
http://localhost:5173
```

## Current Baseline

- Backend
  - `GET /health`
  - `GET /api/questions`
  - `POST /api/questions`
  - `GET /api/practice/ping`
- Frontend
  - Home / Questions / Practice pages
  - Questions page supports adding and listing questions
- Database
  - MySQL + Alembic migration initialized
  - Existing tables: `questions`, `alembic_version`

## Roadmap (Planned)

- AI import
  - `POST /api/import/preview`
  - `POST /api/import/commit`
  - Source text -> structured JSON -> dedupe -> persist
- Practice flow
  - Session creation
  - Draw question by filters
  - Submit answer and score
- AI grading
  - Structured rubric scoring
  - Wrongbook auto update
  - Mastery score update
- Progress dashboard
  - Overall progress
  - Category progress
  - Weak area insights

## Deployment

### Option A: Local (current)

- Backend: `uvicorn app.main:app --reload --port 8000`
- Frontend: `npm run dev`
- DB: Local MySQL `interviewCollector`

### Option B: Production (recommended)

- Backend: Docker image + Gunicorn/Uvicorn workers
- Frontend: `npm run build` static files via Nginx
- Database: managed MySQL
- Environment
  - `DATABASE_URL`
  - `AI_BASE_URL`
  - `AI_MODEL`
  - `AI_API_KEY`
  - `CORS_ORIGINS`

## Dedicated API Document

- Primary API doc file: `docs/api-reference.md`
- Rule: every backend API change must update this file in the same commit

## Doubao (Volcengine Ark) Integration Notes

- Current project env already switched to Ark-compatible defaults:
  - `AI_BASE_URL=https://ark.cn-beijing.volces.com/api/v3`
  - `AI_MODEL=your_ark_endpoint_id`
- In Ark console, use your endpoint/model deployment id to replace `AI_MODEL`.
- Detailed integration and prompt templates: `docs/ai-doubao-integration.md`
