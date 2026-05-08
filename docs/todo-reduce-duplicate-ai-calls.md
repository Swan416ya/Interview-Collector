# 执行清单：减少重复 AI 调用

对应总表：[feature-roadmap-tasks-and-tech.md §1](./feature-roadmap-tasks-and-tech.md)。

**实现进度**：阶段 A、B、C、D 及 **§1 收尾增强** 已在代码中落地（见下方 `[x]`）。

**目标**：在不换模型、不改 Ark 协议的前提下，少打「参考答案」等可缓存或可跳过的远程调用。

**涉及代码（主要）**

- `backend/app/services/ai_service.py` — `call_doubao_reference_answer`（底层仍仅此一处调模型）
- `backend/app/api/import_routes.py` — 导入入库
- `backend/app/api/question_routes.py` — 手动建题、补全参考答案
- `backend/app/api/practice_routes.py` — 阅卷（会话重复提交返回 200 + `grading_reused`）

---

## 阶段 A：参考答案（优先）

| Step | 任务 | 验收 | 状态 |
|------|------|------|------|
| A1 | 抽出统一 **`stem_fingerprint`**（与预览去重同一规则：`strip` + 小写 + 去空白） | 单测或手工：`"A  B"` 与 `"a b"` 同指纹 | `[x]` → `backend/app/core/stem_norm.py` |
| A2 | 新增 **`resolve_reference_for_stem`**：若 `existing_reference` 非空则**不调 AI**；否则查 **batch 内存 dict**（按 fingerprint），命中则复用；未命中再 `call_doubao_reference_answer` 并写入 dict | 单测：同指纹两次只触发一次 mock/真实调用 | `[x]` → `backend/app/services/reference_answer_resolver.py` |
| A3 | **`POST /api/import/commit`**：循环外创建 `dict`，传入 `_insert_single_import_question`，批量内同题干只生成一次参考答案 | 抓包或 log：一批 3 条重复 stem 仅 1 次 reference API | `[x]` → `import_routes.py` |
| A4 | **`POST /api/import/commit-one`**：单条仍走 resolver（`reference_cache=None`，行为与现网一致） | 单条导入仍正常 | `[x]` |
| A5 | **`POST /api/questions/backfill-reference-answers`**：单次请求内对 fingerprint 做 dict 去重，多条同题干只调一次 AI | `limit` 内含重复 stem 时调用次数减少 | `[x]` → `question_routes.py` |
| A6 | **结构化日志**：在「跳过 AI」分支打 `logger.info`（`reason=already_present` / `batch_cache`） | 日志可 grep | `[x]` |

**说明**：`POST /api/questions` 已支持可选 **`reference_answer`**；非空则跳过 AI（经 `resolve_reference_for_stem`）。

---

## 阶段 E：§1 收尾（可选增强 → 已做）

| Step | 任务 | 验收 | 状态 |
|------|------|------|------|
| E1 | **`POST /api/questions`** 请求体可选 `reference_answer` | 非空不调 `call_doubao_reference_answer` | `[x]` |
| E2 | **会话 submit/skip 重复**：由 409 改为 **200** + 已有 `record` + `grading_reused=true` | 连点不报错、不调阅卷 | `[x]` |
| E3 | **`import/preview` 前清理** `import_extract_cache` 过期行 | `delete` + `commit`，打 log | `[x]` |
| E4 | **`ai_service` 统一 prepare/start 日志** | `ai_call_prepare` / `ai_call_start` 含长度字段 | `[x]` |

---

## 阶段 B：导入预览缓存（可选 · 省连点预览）

| Step | 任务 | 验收 | 状态 |
|------|------|------|------|
| B1 | 定义缓存键：`SHA256(当前完整抽取 prompt + 分隔符 + chunk 文本)`，与分类/岗位白名单联动 | 白名单变更即新 key | `[x]` |
| B2 | 存储：`import_extract_cache` 表（`cache_key`, `payload_json`, `expires_at`） | Alembic `g9b0c1d2e3f4` | `[x]` |
| B3 | `POST /api/import/preview`：按 chunk 查/写缓存；响应带 `extract_cache_hits` / `extract_cache_misses` | 默认 TTL 1800s，见 `IMPORT_PREVIEW_CACHE_*` | `[x]` |

---

## 阶段 C：阅卷幂等（核对 + 可选增强）

| Step | 任务 | 验收 | 状态 |
|------|------|------|------|
| C1 | ~~409~~ **已演进**：同会话同题重复 submit/skip 返回 **200** + 已有 `record`、`grading_reused=true`（见阶段 E2） | 不再用 409 挡连点 | `[x]` |
| C2 | **每日练习** `daily/submit`：同题 + 同 `user_answer` + `created_at` 在 `PRACTICE_DAILY_IDEMPOTENCY_SECONDS` 内则复用上条阅卷，响应 `grading_reused=true` | 见 `practice_routes.submit_daily_answer` | `[x]` |

---

## 阶段 D：文档与联调

| Step | 任务 | 验收 | 状态 |
|------|------|------|------|
| D1 | 若 API 行为或响应字段有变，更新 **`docs/api-reference.md`** | CI/人工对照 | `[x]` |
| D2 | 在 [feature-roadmap-tasks-and-tech.md](./feature-roadmap-tasks-and-tech.md) §1 链到本 todo | 双向链接 | `[x]` |
| D3 | **README**：增加「减负 / 联调」索引（本 todo、`api-reference`、相关 `IMPORT_*` / `PRACTICE_*` 环境变量） | 新开发者可按表配置 | `[x]` |
| D4 | **`docs/api-design.md`**：声明「已实现契约以 `api-reference` 为准」并链到减负与延迟说明 | 不与 api-reference 打架 | `[x]` |
| D5 | **`docs/ai-latency-and-streaming.md`**：延迟原因、流式可行性、体感优化与后续清单 | 见该文 | `[x]` |
| D6 | **pytest 基线**：`requirements-dev.txt` + `tests/test_stem_norm.py`、`tests/test_reference_answer_resolver.py` | `cd backend && pip install -r requirements-dev.txt && pytest` 通过 | `[x]` |

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-05-08 | 初版：分阶段 checklist |
| 2026-05-08 | 阶段 A + C1 + D1/D2 已落地：`stem_norm`、`reference_answer_resolver`、import commit 批量缓存、backfill 内缓存、`api-reference` 说明 |
| 2026-05-08 | 阶段 B：`import_extract_cache` + `import_preview` 按 chunk 缓存 + 环境变量 + `api-reference` |
| 2026-05-08 | 阶段 C2：`daily/submit` 短时幂等 + `grading_reused` + `PRACTICE_DAILY_IDEMPOTENCY_*` |
| 2026-05-08 | 阶段 D 补全：README/api-design、ai-latency-and-streaming、pytest 基线、前端等待文案 |
| 2026-05-08 | 阶段 E：手动建题可选参考答案、会话重复 200+grading_reused、预览前 purge、ai_call_prepare 日志、pytest |
