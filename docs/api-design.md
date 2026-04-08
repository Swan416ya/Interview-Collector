# API Design (Draft)

This file describes upcoming API design decisions.
For current implemented APIs, see `docs/api-reference.md`.

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

