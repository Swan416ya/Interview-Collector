# 执行清单：减少重复 AI 调用

对应总表：[feature-roadmap-tasks-and-tech.md §1](./feature-roadmap-tasks-and-tech.md)。

**实现进度**：阶段 A（参考答案批量去重 + backfill 内去重 + 日志）已在代码中落地，见下方 `[x]`。阶段 B/C2/D 仍待做。

**目标**：在不换模型、不改 Ark 协议的前提下，少打「参考答案」等可缓存或可跳过的远程调用。

**涉及代码（主要）**

- `backend/app/services/ai_service.py` — `call_doubao_reference_answer`（底层仍仅此一处调模型）
- `backend/app/api/import_routes.py` — 导入入库
- `backend/app/api/question_routes.py` — 手动建题、补全参考答案
- `backend/app/api/practice_routes.py` — 阅卷（会话提交已有 409，核对文档即可）

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

**说明**：手动 `POST /api/questions` 创建题目当前无「自带参考答案」字段，仍每次生成；若后续增加可选 `reference_answer` 入参，再在 resolver 里接 `existing_reference` 即可。

---

## 阶段 B：导入预览缓存（可选 · 省连点预览）

| Step | 任务 | 验收 | 状态 |
|------|------|------|------|
| B1 | 定义缓存键：`hashlib.sha256(f"{prompt_version}:{raw_text}".encode()).hexdigest()`（`prompt_version` 可用常量或 git short hash） | 文档写清版本 bump 规则 | `[ ]` |
| B2 | 存储：`import_extract_cache` 表（`key`, `payload_json`, `expires_at`）或进程内 LRU（仅单机 dev） | 同一原文连续 preview 第二次不调 `call_doubao_extract` | `[ ]` |
| B3 | `POST /api/import/preview`：先查缓存，命中直接返回；未命中写缓存 | TTL 建议 15–60 分钟 | `[ ]` |

---

## 阶段 C：阅卷幂等（核对 + 可选增强）

| Step | 任务 | 验收 | 状态 |
|------|------|------|------|
| C1 | 确认 **`POST .../sessions/{id}/submit`** 已对 `session_id + question_id` 返回 **409** | 文档本页打勾；无需改代码则标「已满足」 | `[x]`（`practice_routes.submit_answer` 已存在） |
| C2 |（可选）**每日练习** `daily/submit`：若需防连点，再定义策略（如「同题同答案 60s 内返回上条结果」） | 产品确认后再做 | `[ ]` |

---

## 阶段 D：文档与联调

| Step | 任务 | 验收 | 状态 |
|------|------|------|------|
| D1 | 若 API 行为或响应字段有变，更新 **`docs/api-reference.md`** | CI/人工对照 | `[x]`（已补充 commit / backfill 行为说明） |
| D2 | 在 [feature-roadmap-tasks-and-tech.md](./feature-roadmap-tasks-and-tech.md) §1 小项表可加「见 todo-reduce-duplicate-ai-calls」 | 双向链接 | `[x]` |

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-05-08 | 初版：分阶段 checklist |
| 2026-05-08 | 阶段 A + C1 + D1/D2 已落地：`stem_norm`、`reference_answer_resolver`、import commit 批量缓存、backfill 内缓存、`api-reference` 说明 |
