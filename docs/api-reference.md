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
- Description:
  - list questions with filter and sorting
  - `sort_by` supports: `created_at`, `mastery_score`, `recent_encountered`
  - `recent_encountered` means sort by latest practice record time
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

### List Questions (Paginated)

- Method: `GET`
- Path: `/api/questions/page`
- Query:
  - `page` (>=1)
  - `page_size` (1-100)
  - `category` (optional)
  - `difficulty` (optional)
  - `sort_by` / `sort_order` (same as `/api/questions`)
- Description:
  - return paged result for question-bank page, avoid loading all questions at once
- Response example:

```json
{
  "total": 238,
  "page": 2,
  "page_size": 20,
  "items": [
    { "id": 21, "stem": "示例题目", "category": "计算机网络", "difficulty": 3 }
  ]
}
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

### Practice Activity Heatmap (daily question count)

- Method: `GET`
- Path: `/api/practice/activity`
- Description:
  - returns a **dense** list of **371** calendar days (53 weeks × 7 days) for a GitHub-style heatmap
  - dates use **`Asia/Shanghai`** (calendar date, not UTC)
  - window: from the Sunday of the week **52 weeks before** the Sunday of the current week, through **Saturday** of the current week (inclusive of all cells in the grid)
  - **`count`**: number of `practice_records` rows whose `created_at` falls on that calendar day in Shanghai (each submit, skip, or daily submit counts as one)
  - **`level`**: `0` gray (0 questions or future days); `1` 1–9; `2` 10–19; `3` 20–49; `4` 50+
  - **`total_questions`**: sum of `count` over the window (only days ≤ `today` contribute non-zero counts; future cells are `0`)
  - **`active_days`**: days in the window with `count > 0` and `date ≤ today`
- Response example:

```json
{
  "timezone": "Asia/Shanghai",
  "start_date": "2025-04-06",
  "end_date": "2026-04-11",
  "today": "2026-04-11",
  "total_questions": 128,
  "active_days": 42,
  "days": [
    { "date": "2025-04-06", "count": 0, "level": 0 },
    { "date": "2025-04-07", "count": 3, "level": 1 }
  ]
}
```

### Practice Categories (for training selector)

- Method: `GET`
- Path: `/api/practice/categories`
- Description:
  - return each category with question count
  - `selectable=true` only when question count is at least 10
- Response example:

```json
[
  { "category": "计算机网络", "total_questions": 23, "selectable": true },
  { "category": "操作系统", "total_questions": 8, "selectable": false }
]
```

### Start Practice Session

- Method: `POST`
- Path: `/api/practice/sessions/start`
- Query (optional):
  - `category`: start a 10-question session from this category
- Description:
  - random pick 10 questions
  - if category is set and count < 10, return 400

### Start Custom Practice Session

- Method: `POST`
- Path: `/api/practice/sessions/start/custom`
- Request body:

```json
{
  "question_ids": [11, 29, 7, 54, 82, 15, 33, 60, 41, 22]
}
```

- Description:
  - start session with exactly 10 specified question ids
  - used by memorize mode ("背题 10 题后乱序测验")

### Submit Practice Answer

- Method: `POST`
- Path: `/api/practice/sessions/{session_id}/submit`
- Description:
  - call AI grading
  - AI grading input only includes question stem + user answer (does not include reference answer)
  - save `PracticeRecord`
  - update question mastery score by formula:
    - `new_mastery = old_mastery * 0.7 + latest_score(0-100) * 0.3`

### Daily Question Submit

- Method: `POST`
- Path: `/api/practice/daily/submit`
- Request body:

```json
{
  "question_id": 123,
  "user_answer": "我的作答..."
}
```

- Description:
  - AI judge one daily question answer immediately
  - AI grading input only includes question stem + user answer (does not include reference answer)
  - create one `PracticeRecord` with `session_id = null`
  - return score/analysis/reference_answer
  - update mastery by the same formula

### Skip Practice Answer (score 0)

- Method: `POST`
- Path: `/api/practice/sessions/{session_id}/skip`
- Request body:

```json
{
  "question_id": 123
}
```

- Description:
  - when user clicks next without grading, record this question as skipped
  - create a practice record with `ai_score=0`
  - this 0 score is included in session total score and mastery update formula

### Practice Session Summary

- Method: `GET`
- Path: `/api/practice/sessions/{session_id}/summary`

### Practice Session List

- Method: `GET`
- Path: `/api/practice/sessions`
- Description: list completed sessions only

### Practice Session Records

- Method: `GET`
- Path: `/api/practice/sessions/{session_id}/records`
- Description: return full records for one session

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
  - **category**：若 AI 返回的名称不在本地分类表中，自动改为 **「未分类」**（若存在），否则改为字典序第一个分类；不会因此返回 400
  - **roles**：仅保留本地岗位表中存在的名称；可退化为空列表；不会因此返回 400
  - companies: link if exists, create if not
  - each imported question auto-generates `reference_answer` via AI
- Response extra fields:
  - `category_fallbacks`: 发生分类回退的题目数量
  - `role_lists_adjusted`: 岗位列表被裁剪过的题目数量

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

- no pending API in this module (already implemented)

### Progress / Wrongbook

- `GET /api/progress/overview`
- `GET /api/progress/categories`
- `GET /api/wrongbook`
