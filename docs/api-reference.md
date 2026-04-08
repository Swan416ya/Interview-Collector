# API Reference (Living Document)

This document is the single source of truth for backend APIs.
When any API is added/removed/changed, update this file in the same commit.

## Base

- Local base URL: `http://localhost:8000`
- Swagger: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`

## Current APIs

### Health

- Method: `GET`
- Path: `/health`
- Description: Service liveness check
- Response example:

```json
{
  "status": "ok",
  "env": "dev"
}
```

### List Questions

- Method: `GET`
- Path: `/api/questions`
- Description: List questions by latest id desc
- Response example:

```json
[
  {
    "id": 1,
    "stem": "TCP 三次握手为什么不是两次？",
    "category": "计算机网络",
    "difficulty": 3
  }
]
```

### Create Question

- Method: `POST`
- Path: `/api/questions`
- Description: Create a new question
- Note: backend will call AI to generate and save `reference_answer`
- Request body:

```json
{
  "stem": "什么是进程和线程？",
  "category": "操作系统",
  "difficulty": 3
}
```

- Response example:

```json
{
  "id": 2,
  "stem": "什么是进程和线程？",
  "category": "操作系统",
  "difficulty": 3
}
```

### Practice Ping

- Method: `GET`
- Path: `/api/practice/ping`
- Description: Placeholder endpoint for practice module
- Response example:

```json
{
  "message": "practice module ready"
}
```

### Categories CRUD

- `GET /api/categories`
- `POST /api/categories`
- `PUT /api/categories/{category_id}`
- `DELETE /api/categories/{category_id}`

### Roles CRUD

- `GET /api/roles`
- `POST /api/roles`
- `PUT /api/roles/{role_id}`
- `DELETE /api/roles/{role_id}`

### Import Prompt Template

- Method: `GET`
- Path: `/api/import/prompt-template`
- Description:
  - returns dynamic prompt with local category/role whitelist
  - enforces full company name output

### Import Commit

- Method: `POST`
- Path: `/api/import/commit`
- Description:
  - category/roles must be in local data
  - companies: link if exists, create if not
  - each imported question auto-generates `reference_answer` via AI

### Backfill Missing Reference Answers

- Method: `POST`
- Path: `/api/questions/backfill-reference-answers`
- Query:
  - `limit` (default 50, max 500)
- Description:
  - scan questions with empty `reference_answer`
  - call AI to generate and fill missing reference answers

### Import Preview (AI Extract)

- Method: `POST`
- Path: `/api/import/preview`
- Request body:

```json
{
  "raw_text": "面经原文..."
}
```

- Description:
  - backend calls Doubao (Ark Responses API)
  - returns extracted `questions` JSON for user review
  - frontend should default-select all extracted questions

## Planned APIs (Next Iteration)

### AI Import

- `POST /api/import/preview`
- (current implemented) `POST /api/import/commit`

### Practice Session

- `POST /api/practice/sessions`
- `GET /api/practice/sessions/{id}/next`
- `POST /api/practice/submit`

### Progress / Wrongbook

- `GET /api/progress/overview`
- `GET /api/progress/categories`
- `GET /api/wrongbook`
