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
  - `sort_by` supports: `created_at`, `mastery_score`, `recent_encountered`, `id`
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

### Practice Activity Heatmap (daily practice record counts)

- Method: `GET`
- Path: `/api/practice/activity`
- Description:
  - returns a **dense** list of **371** calendar days (53 weeks × 7 days) for a GitHub-style heatmap
  - **`count` per cell** uses the **storage calendar date** of `created_at` — same as SQL `date(created_at)` (SQLite `date(created_at)`). This matches raw DB tools that filter `WHERE date(created_at) = '…'`. It does **not** reinterpret naive timestamps as UTC and then convert to Shanghai (which could shift rows across midnight and make totals disagree with DB date filters).
  - **`timezone` field** in JSON is informational (`storage-date(created_at)`); **`today`** is still **Asia/Shanghai** wall date for greying out future cells in the grid.
  - window: from the Sunday of the week **52 weeks before** the Sunday of the current week, through **Saturday** of the current week (inclusive of all cells in the grid)
  - **`count`**: number of `practice_records` rows with that `date(created_at)` (each submit, skip, or daily submit counts as one row; **the same question can contribute multiple times** if practiced multiple times that day)
  - **`level`**: `0` gray (0 questions or future days); `1` 1–9; `2` 10–19; `3` 20–49; `4` 50+
  - **`total_questions`**: sum of `count` over the window (only days ≤ `today` contribute non-zero counts; future cells are `0`)
  - **`active_days`**: days in the window with `count > 0` and `date ≤ today`
- Response example:

```json
{
  "timezone": "storage-date(created_at)",
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

### Practice answer log (paginated, reconcile heatmap)

- Method: `GET`
- Path: `/api/practice/records`
- Query:
  - `page` (>=1, default 1)
  - `page_size` (1–200, default 20)
  - `shanghai_date` (optional): `YYYY-MM-DD`; same as SQL `date(created_at)` (same bucketing as `/api/practice/activity` cells)
- Description:
  - Every row in `practice_records` (session submit, session skip, daily submit), newest first
  - Includes `question_stem` (or placeholder if the question row was removed)
  - Filtering by `shanghai_date` makes **`total`** match the heatmap **`count`** for that calendar date
- Response example:

```json
{
  "total": 128,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": 501,
      "session_id": 12,
      "question_id": 3,
      "question_stem": "TCP 三次握手…",
      "user_answer": "…",
      "ai_score": 7,
      "created_at": "2026-04-11T08:15:00"
    }
  ]
}
```

### Practice Categories (for training selector)

- Method: `GET`
- Path: `/api/practice/categories`
- Description:
  - returns `{ "categories": [...], "total_questions_all": N }`
  - each category: `total_questions`, `selectable` (true when count ≥ 5, i.e. enough for smallest session)
  - `total_questions_all`: all questions across categories (for “全部分类随机”题量校验)
- Response example:

```json
{
  "categories": [
    { "category": "计算机网络", "total_questions": 23, "selectable": true },
    { "category": "操作系统", "total_questions": 4, "selectable": false }
  ],
  "total_questions_all": 120
}
```

### Start Practice Session

- Method: `POST`
- Path: `/api/practice/sessions/start`
- Query (optional):
  - `category`: limit pool to this category; omit for all categories
  - `count`: **5, 10, or 15** (default `10`)
- Description:
  - random pick `count` questions
  - persists `practice_sessions.question_count` for completion logic (session completes when that many records exist)
  - if pool has fewer than `count` questions, return 400 with clear message
- Response includes `question_count` (same as `count`)

### Start Custom Practice Session

- Method: `POST`
- Path: `/api/practice/sessions/start/custom`
- Request body:

```json
{
  "question_ids": [11, 29, 7, 54, 82]
}
```

- Description:
  - `question_ids` length must be **5, 10, or 15** (unique ids)
  - `question_count` on the session is set to that length
  - used by memorize mode after “背题”：前端按所选 5/10/15 题传入对应数量的 `question_ids`

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
- Response includes `question_count`; max score = `question_count * 10`

### Practice Session List

- Method: `GET`
- Path: `/api/practice/sessions`
- Description: list completed sessions only; each item includes `question_count`

### Practice Session Records

- Method: `GET`
- Path: `/api/practice/sessions/{session_id}/records`
- Description: return full records for one session; includes `question_count`

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

### Import Commit (batch)

- Method: `POST`
- Path: `/api/import/commit`
- Description:
  - **category**：若 AI 返回的名称不在本地分类表中，自动改为 **「未分类」**（若存在），否则改为字典序第一个分类；不会因此返回 400
  - **roles**：仅保留本地岗位表中存在的名称；可退化为空列表；不会因此返回 400
  - companies: link if exists, create if not
  - each imported question gets `reference_answer` via AI **unless** another item in the **same request** already generated one for the same **stem fingerprint**（规范化题干：小写、去空白），此时复用同一段参考答案，**不重复调用**参考答案模型
  - 同一事务内处理全部题目；任一题失败则整批回滚
- Response extra fields:
  - `category_fallbacks`: 发生分类回退的题目数量
  - `role_lists_adjusted`: 岗位列表被裁剪过的题目数量

### Import Commit One (single question)

- Method: `POST`
- Path: `/api/import/commit-one`
- Request body: 与 `ImportQuestionItem` 相同（`stem`, `category_name`, `roles`, `companies`, `difficulty`）
- Description:
  - 仅处理一道题：生成参考答案 → 写入 `questions` 与关联表 → **立即 `commit`**
  - 分类/岗位规则与 `/api/import/commit` 相同
  - 适合前端「逐题导入」，避免一题 AI/解析失败导致已生成题目全部丢失
- Response: `ImportCommitOneResponse`（`id`, `stem`, `category`, `difficulty`, `category_fallback`, `roles_adjusted`, `linked_roles`, `linked_companies`, `created_companies`）

### Backfill Missing Reference Answers

- Method: `POST`
- Path: `/api/questions/backfill-reference-answers`
- Query:
  - `limit` (default 50, max 500)
- Description:
  - scan questions with empty `reference_answer`
  - call AI to generate and fill missing reference answers
  - 单次请求内若多条候选题干经 **stem fingerprint** 相同，仅对第一条调用 AI，其余复用（减少重复计费）

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
