# API Design (Draft)

This file describes upcoming API design decisions.

**Implemented HTTP contracts** are maintained in [`docs/api-reference.md`](./api-reference.md) and must be updated in the same commit as backend route changes (see root `README.md`).

**Related notes**

- Reduce duplicate AI calls (caching / idempotency checklist): [`docs/todo-reduce-duplicate-ai-calls.md`](./todo-reduce-duplicate-ai-calls.md)
- Latency and optional streaming direction: [`docs/ai-latency-and-streaming.md`](./ai-latency-and-streaming.md)

## Planned Modules

- Import:
  - `POST /api/import/preview`
  - `POST /api/import/commit`
- Practice:
  - `POST /api/practice/sessions`
  - `GET /api/practice/sessions/{id}/next`
  - `POST /api/practice/submit`
- Progress:
  - `GET /api/progress/overview`
  - `GET /api/progress/categories`
  - `GET /api/wrongbook`

