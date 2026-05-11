# 功能拆解清单与技术栈（同步学习用）

本文档把 [AI 进化与第二大脑愿景](./ai-evolution-second-brain.md) 中的能力拆成**可逐个实现的小项**，并为每一块标注**当前仓库已用技术**与**实现时可能新增的技术**，便于你边做边学。

**约定（重要）**

- **下文 §1 → §12 的章节顺序，即推荐的实现优先级顺序**（靠前先做，靠后可排期/并行学习）。
- **当前阶段**：不折腾「换模型 / 多厂商路由」；AI 仍用现有 Ark + `doubao-seed-2.0-lite`。
- **题库去重**：整体**后挪**（见 §9）；优先用 **§1 减少重复调用** 先省成本与延迟。

**当前仓库技术基线（实现前默认会用到的）**

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端 | Python 3、**FastAPI**、**Pydantic**、**SQLAlchemy 2**、**Alembic** | `backend/app/` |
| 数据库 | **MySQL**、PyMySQL、`cryptography` | 连接串见 `backend/.env` |
| HTTP 客户端 | **httpx** | 调用 Ark/豆包 API，`ai_service.py` |
| 前端 | **Vue 3**、**TypeScript**、**Vite**、**Vue Router**、**Pinia**、**Axios**、**Chart.js**、**marked**、**DOMPurify** | `frontend/` |
| 可选客户端 | **Flutter** | `flutterend/`，与后端联调 |
| AI 提供方 | **火山引擎 Ark**（当前：`doubao-seed-2.0-lite`）、Responses 风格 JSON | 见 [ai-doubao-integration.md](./ai-doubao-integration.md) |

下文「**新增**」指本仓库尚未引入、实现该小项时常需自学接入的依赖或组件（按需，不要求一次全上）。

---

## 1. 减少重复 AI 调用（最高优先级）

**分步执行清单（勾选与备注）**：[todo-reduce-duplicate-ai-calls.md](./todo-reduce-duplicate-ai-calls.md)。

**业务目标**：在**不换模型**的前提下，降低参考答案、抽取、阅卷等路径的冗余计费与延迟；同一输入不反复打远程。

### 1.1 小项清单

| 序号 | 小项 | 验收标准（建议） |
|------|------|------------------|
| 1.1.1 | **参考答案**：入库/补全前若 `reference_answer` 已非空则**跳过** `call_doubao_reference_answer` | 导入、`backfill`；**`POST /api/questions` 可选 `reference_answer`** 手写则跳过 AI |
| 1.1.2 | **同一请求内去重**：批量导入中多条 **stem 规范化后相同** 只生成一次 reference，其余复用字符串 | 内存 dict 即可 MVP |
| 1.1.3 | **抽取预览缓存** | 已实现：按 **SHA256(完整抽取 prompt + chunk)** 写入 `import_extract_cache`（见 [todo-reduce-duplicate-ai-calls.md](./todo-reduce-duplicate-ai-calls.md) 阶段 B） |
| 1.1.4 | **阅卷幂等** | 会话 submit/skip：同会话同题已有记录则 **200** 返回已有 `PracticeRecord`，`grading_reused=true`，不调阅卷；每日：`daily/submit` 时间窗同上（见 [todo-reduce-duplicate-ai-calls.md](./todo-reduce-duplicate-ai-calls.md) 阶段 C） |
| 1.1.5 | **结构化日志（轻量）** | `ai_service`：`ai_call_prepare` + `ai_call_start`（含 `prompt_len`/`user_text_len`/`stem_len`/`answer_len`）；缓存命中路径另有 `logger.info` |

### 1.2 技术栈与学习线索

| 内容 | 技术 |
|------|------|
| 已有 | `import_routes`、`ai_service`、`httpx` |
| 新增 | `hashlib.sha256`、`functools.lru_cache`（仅进程内短缓存）；或 MySQL 表 `ai_response_cache(key, payload, expires_at)` |
| 学习关键词 | *idempotent API*、*request-scoped memoization*、*cache-aside* |

---

## 2. 知识库检索与对话（RAG Copilot，高优先级）

**分步执行清单（勾选与备注）**：[todo-rag-knowledge-copilot.md](./todo-rag-knowledge-copilot.md)。

**业务目标**：尽快打通「**自己的题库文本 → 检索 → 带引用回答**」；多轮与向量后补。

### 2.1 小项清单

| 序号 | 小项 | 验收标准（建议） | 状态 |
|------|------|------------------|------|
| 2.1.1 | **片段表** `document_chunks` | `question_id`、`text`、JSON 元数据（`chunk_meta`）；Alembic 迁移 | √ |
| 2.1.2 | **写入路径**：题目创建/更新、导入成功写入 DB 时，**同步切块写入** chunks（题干一段、参考答案一段等） | 可先仅题干+参考，保证有检索料 | √ |
| 2.1.3 | **关键词检索 MVP** | MySQL **FULLTEXT** + 无命中时 **LIKE/contains**；SQLite 走 contains | √ |
| 2.1.4 | `POST /api/kb/query` | 入参：`query`、`top_k`；出参：`answer` + `citations[]`（`question_id` / `chunk_id` + 摘录） | √ |
| 2.1.5 | **Prompt**：无相关片段则拒答或明确「库中未找到」 | 降低胡编 | √ |
| 2.1.6 | **前端 Copilot 页** | 路由 `/copilot`；`MarkdownRenderer`；引用列表（详见 [todo-rag-knowledge-copilot.md](./todo-rag-knowledge-copilot.md)） | √ |
| 2.1.7 | **向量检索（可选，RAG 增强）** | 云端 embedding + 相似度排序，与关键词结果融合 | 二期 |
| 2.1.8 | **多轮 + SSE（可选）** | `kb_threads` / `kb_messages`；`StreamingResponse` | 二期 |

### 2.2 技术栈与学习线索

| 内容 | 技术 |
|------|------|
| 已有 | FastAPI、httpx、豆包 JSON |
| 新增（检索） | MySQL **FULLTEXT**；或 **Meilisearch** / **Typesense** |
| 新增（向量） | 火山 **Embedding**；相似度 **NumPy** 或手写余弦 |
| 学习关键词 | *RAG*、*citation grounding*、*chunking*、*hybrid search* |

---

## 3. 错题本：准入 / 准出规则（中高优先级）

**业务目标**：错题本**进得合理、出得及时**，避免「一题永错」或「刷一次就丢」。

**实现状态**：§3.1 小项 **3.1.1–3.1.5 均已落地**（后端 `practice_routes.py` + `wrongbook_service.py` + 迁移 `w7b8k9w0r1n2`；前端 `/wrongbook` 与训练中心「仅错题本」题池）。下表「完成」列 `[x]` 表示已验收。

### 3.1 小项清单

| 序号 | 小项 | 验收标准（建议） | 完成 |
|------|------|------------------|------|
| 3.1.1 | **准入规则（可配置常量）** | `WRONGBOOK_ADMIT_MAX_SCORE`（默认 6）、`WRONGBOOK_ADMIT_CONSECUTIVE_LOW`（默认 1，即单次低分即入；设为 2 则需连续两次低分）；**手动** `POST /api/practice/wrongbook/manual` | [x] |
| 3.1.2 | **准出规则** | 最近 `WRONGBOOK_DISCHARGE_STREAK` 次（默认 3）均 `>= WRONGBOOK_DISCHARGE_MIN_SCORE`（默认 8）则 `wrongbook_active=false` 并写 `wrongbook_cleared_at` | [x] |
| 3.1.3 | **状态字段或关联表** | `questions` 上 `wrongbook_active`、`wrongbook_entered_at`、`wrongbook_last_wrong_at`、`wrongbook_cleared_at` | [x] |
| 3.1.4 | **列表 API** | `GET /api/practice/wrongbook?state=in|out|all`；`out` = 已准出（曾入本且已清除） | [x] |
| 3.1.5 | **与练习会话联动** | `POST /api/practice/sessions/start?pool=wrongbook`；`GET /api/practice/categories?pool=wrongbook` | [x] |

### 3.2 技术栈与学习线索

| 内容 | 技术 |
|------|------|
| 已有 | `PracticeRecord`、`ai_score`、`mastery_score` |
| 新增 | 时间窗统计：SQL 子查询或 SQLAlchemy `func.count` + `having`；或每次提交后在 Python 里更新状态机 |
| 学习关键词 | *state machine*、*hysteresis*（防止边界抖动进出） |

---

## 4. 阅卷扩展：每题保留 + 会话结束总评 + 雷达图（中优先级）

**业务目标**：**保留**现有每题打分与短解析；在**每次固定题量（如 10 题）会话全部提交结束后**，追加 **1 次** LLM 生成**总评**（文字 + 多维度分数），前端用 **Chart.js 雷达图**展示；**全局**多维雷达为**更后期**（见 §8）。

**实现状态**：§4.1 小项 **4.1.1–4.1.4 已落地**（`session_summary_service.py`、`ai_service.call_doubao_session_summary`、迁移 `m1n2s3u4m5r6`、`PracticeView` / `PracticeHistoryView` 雷达图 + Markdown）。4.1.5 仍为可选增强。

### 4.1 小项清单

| 序号 | 小项 | 验收标准（建议） | 完成 |
|------|------|------------------|------|
| 4.1.1 | **会话维度聚合** | 会话完成时收集 10 题的 `stem` / `ai_score` / 可选 `user_answer` 摘要 | [x] |
| 4.1.2 | **单次总评 LLM** | `call_doubao_session_summary(...)` → JSON：`summary_text`、`dimensions`（**5** 维固定键，0–10） | [x] |
| 4.1.3 | **持久化** | `practice_sessions.session_feedback_json` + `summary_done`；`GET .../summary` 幂等补全 | [x] |
| 4.1.4 | **前端：会话结束页雷达图** | Chart.js **radar**；总评 Markdown；历史记录详情同显 | [x] |
| 4.1.5 | **（可选）每题 Rubric 扩展** | 仍用单次阅卷 API，逐步增加 `missed_points` 等字段；与总评维度尽量对齐，便于叙事一致 | [ ] |
| 4.1.6 | **全局雷达（低优，见 §8）** | 不在本阶段阻塞上线 |

### 4.2 技术栈与学习线索

| 内容 | 技术 |
|------|------|
| 已有 | `call_doubao_grade`、`PracticeSession`、Chart.js |
| 新增 | Pydantic 校验 session summary JSON；会话「完成」钩子（最后一题 submit 或 `summary` 接口触发） |
| 学习关键词 | *session-level evaluation*、*radar chart*、*single-shot batch summarization* |

---

## 5. AI 调用薄封装与可观测（中优先级 · 不做换模型）

**业务目标**：超时、重试、JSON 解析集中维护；**不**引入多模型环境变量（当前明确不做）。

### 5.1 小项清单

| 序号 | 小项 | 验收标准（建议） |
|------|------|------------------|
| 5.1.1 | 抽出 `call_llm_json(...)` 或类 `ArkResponsesClient` | `extract` / `grade` / `session_summary` / `kb_query` 共用 |
| 5.1.2 | **结构化日志** | `latency_ms`、错误码、是否跳过缓存；仍用 Python `logging` 即可 |
| 5.1.3 | **（删除项）** 分场景多 `AI_MODEL_*` | **暂不实施**，避免范围蔓延 |

### 5.2 技术栈与学习线索

| 内容 | 技术 |
|------|------|
| 已有 | `httpx`、`settings`、`logging` |
| 学习关键词 | *DRY*、*defensive parsing* |

---

## 6. 导入管线增强（任务、容错；与 §9 去重解耦）

**业务目标**：大批量导入可追踪；**与 §1 缓存叠加**进一步省钱。

### 6.1 小项清单

| 序号 | 小项 | 验收标准（建议） |
|------|------|------------------|
| 6.1.1 | 导入任务表 `import_task`（若尚无） | `status`、计数、错误摘要 |
| 6.1.2 | 批量 commit **逐条结果** | 返回每条成功/失败原因，便于前端重试失败项 |
| 6.1.3 | **异步导入（可选）** | Celery/RQ 或 `BackgroundTasks` |

### 6.2 技术栈与学习线索

| 内容 | 技术 |
|------|------|
| 新增 | **Celery** + **Redis** / **RQ**；或 FastAPI 后台任务 |
| 学习关键词 | *partial batch success*、*job queue* |

---

## 7. 掌握度、薄弱统计与 SRS（中后优先级）

**业务目标**：`mastery_score` 规则清晰；分类级统计；为错题与总评提供数据基础。

### 7.1 小项清单

| 序号 | 小项 | 验收标准（建议） |
|------|------|------------------|
| 7.1.1 | 提交后更新 `mastery_score` 文档化公式 | README 或 `docs/` 一页写清 |
| 7.1.2 | 分类维度聚合 API | `avg(mastery)`、`wrong_rate` by category |
| 7.1.3 | **SRS 字段（可选）** | `next_review_at` 等 |

### 7.2 技术栈与学习线索

| 内容 | 技术 |
|------|------|
| 已有 | `mastery_score`、活动 heatmap API |
| 学习关键词 | *spaced repetition*、*learning analytics* |

---

## 8. 全局掌握度雷达与长期画像（较低优先级）

**业务目标**：跨多次会话汇总各维度，**全局**雷达图 / 趋势；依赖 §4 的维度定义一致。

### 8.1 小项清单

| 序号 | 小项 | 验收标准（建议） |
|------|------|------------------|
| 8.1.1 | 聚合已持久化的 `session_feedback_json` | 按时间窗（如近 30 天）求维度均值 |
| 8.1.2 | **全局雷达 API + 页面** | 与单次会话雷达复用 Chart.js 配置 |
| 8.1.3 | **与个人目标差距（可选）** | 静态阈值或用户设定目标分 |

### 8.2 技术栈与学习线索

| 内容 | 技术 |
|------|------|
| 已有 | Chart.js radar |
| 新增 | SQL `AVG` over JSON 列（MySQL `JSON_TABLE` 或应用层聚合） |

---

## 9. 题目去重（整体后挪 · 中低优先级）

**业务目标**：库内重复行减少；与 §1 不同，本节解决**数据质量**而非单次调用浪费。

### 9.1 小项清单

| 序号 | 小项 | 验收标准（建议） |
|------|------|------------------|
| 9.1.1 | `stem_normalized` 或 `content_hash` + 索引 | Alembic |
| 9.1.2 | `commit` / `commit-one` **对库查重** | 命中返回 `duplicate_of_id`，默认跳过 |
| 9.1.3 | 预览阶段 `maybe_duplicate_ids`（先做规范化相等） |  |
| 9.1.4 | 语义去重 / 合并向导（可选） | embedding 或 SimHash；合并 UI |

### 9.2 技术栈与学习线索

| 内容 | 技术 |
|------|------|
| 新增 | `hashlib`、embedding、SimHash |
| 学习关键词 | *near-duplicate detection* |

---

## 10. 简历驱动的针对性组题（后期）

**业务目标**：简历 → 技能结构化 → 组卷 → 对接现有 `practice/sessions/start`。

### 10.1 小项清单

（同前版：解析、映射、组卷、开练；**组卷去重可与 §9 联动**。）

| 序号 | 小项 | 验收标准（建议） |
|------|------|------------------|
| 10.1.1 | `POST /api/resume/parse` → JSON | 技能、项目、意向 |
| 10.1.2 | 技能 → 分类映射 | 规则表 + 可选 LLM |
| 10.1.3 | 组卷算法 + 练习 API |  |

### 10.2 技术栈与学习线索

| 内容 | 技术 |
|------|------|
| 新增 | `UploadFile`、**pypdf** / **pdfplumber**（若需要 PDF） |

---

## 11. 模拟面试多轮（可选 · 后期）

**业务目标**：多轮追问状态机；可复用 §2 RAG 片段控制 token。

### 11.1 小项清单

（同前版 §8：状态机、RAG 上下文、结束总结。）

### 11.2 技术栈与学习线索

| 内容 | 技术 |
|------|------|
| 新增 | `Enum` 状态转移 |

---

## 12. 质量与工程化（贯穿；与功能并行）

### 12.1 小项清单

| 序号 | 小项 | 验收标准（建议） |
|------|------|------------------|
| 12.1.1 | **pytest** 覆盖缓存分支、RAG 检索、错题状态机 | 基线：`backend/requirements-dev.txt` + `tests/test_stem_norm.py`、 `tests/test_reference_answer_resolver.py`（`cd backend && pytest`） |
| 12.1.2 | API 变更同步 **`docs/api-reference.md`** | 仓库约定 |

### 12.2 技术栈与学习线索

| 内容 | 技术 |
|------|------|
| 新增 | **pytest**、FastAPI `TestClient` |

---

## 13. 与主愿景文档的关系

| 文档 | 用途 |
|------|------|
| [ai-evolution-second-brain.md](./ai-evolution-second-brain.md) | 为什么做、阶段划分、成本与定价附录 |
| **本文档** | **按优先级排序**的小项 + 技术栈 + 学习关键词 |

---

## 14. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-05-08 | 初版：按功能拆解小项 + 技术栈与学习线索 |
| 2026-05-08 | **重排**：章节顺序 = 实现优先级；§1 减重复 AI；RAG 提前；错题准入准出；阅卷会话总评+雷达；全局雷达后挪；去重后挪；明确暂不换模型 |
| 2026-05-08 | §1 链接 [todo-reduce-duplicate-ai-calls.md](./todo-reduce-duplicate-ai-calls.md)；参考答案批量/补全去重已在代码落地 |
| 2026-05-08 | §1.1.3：`import_extract_cache` + preview 按 chunk 缓存、`IMPORT_PREVIEW_CACHE_*`、前端提示 |
| 2026-05-08 | §1.1.4：daily 短时阅卷幂等 + `grading_reused` + `PRACTICE_DAILY_IDEMPOTENCY_*` |
| 2026-05-08 | §1 收尾：`POST /questions` 可选参考答案、会话重复 200+`grading_reused`、预览前清理过期 extract 缓存、`ai_call_prepare` 日志、pytest |
| 2026-05-08 | §12 基线 pytest + `ai-latency-and-streaming.md`；README / api-design 联调索引；todo 阶段 D 补全 |
| 2026-05-08 | §2 链接 [todo-rag-knowledge-copilot.md](./todo-rag-knowledge-copilot.md)（RAG 实现步骤） |
