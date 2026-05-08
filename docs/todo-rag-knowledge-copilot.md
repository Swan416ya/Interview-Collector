# 执行清单：知识库检索与对话（RAG Copilot）

对应总表：[feature-roadmap-tasks-and-tech.md §2](./feature-roadmap-tasks-and-tech.md)。  
愿景背景：[ai-evolution-second-brain.md](./ai-evolution-second-brain.md)（L2 索引层 + L3 认知层）。

**业务目标（MVP）**：在「当前题库中的题干 + 参考答案」上完成 **检索 → 组装上下文 → 单次 LLM 回答 → 带来源引用**；不先做向量与多轮，避免一次迭代过大。

**约束**：继续复用现有 Ark/`httpx` 与 `AI_*` 环境变量；新增表与 API 须在 **`docs/api-reference.md`** 与同一提交中维护。

---

## 本步完成的目的与产出

**目的（为什么要做这一步）**

1. **把「题库」变成可检索的知识库**：题目与参考答案不再只在列表里人肉翻，而是能按自然语言问题 **命中相关片段**，为后续「第二大脑」打地基。  
2. **回答可溯源**：模型输出必须 **显式引用** `chunk_id` / `question_id` 对应片段，减少「凭空编考点」的体感，便于你对照原题复习。  
3. **与练习/阅卷解耦**：本能力解决的是 **「问知识库」**；**不替代** 现有「提交作答 → AI 判分」链路（见下文「能力边界」）。

**做完 MVP 后，仓库里会多出什么（产出清单）**

| 产出 | 说明 |
|------|------|
| 表 **`document_chunks`** + 迁移 | 存可检索文本块及与题目的关联 |
| **同步逻辑** | 题目增删改、导入后自动更新 chunks（或 + 一次 reindex） |
| **`POST /api/kb/query`** | 入参：用户问题；出参：回答文本 + `citations[]` |
| **前端 Copilot 页** | 输入问题、展示回答与引用列表（可链到题目详情） |
| 文档 **`api-reference.md` 更新** + 可选 pytest | 与仓库约定一致 |

---

## 能力边界：和「聊天」「判题」「少调模型」的关系

### 能不能做「聊天页」、和 AI 交流知识库里的内容？

- **可以。** MVP 形态是：**单轮**——用户发一条问题 → 后端检索 chunks → 调 **一次** 大模型生成回答 + 引用。  
- 页面上就是典型的「输入框 + 发送 + 消息区」，语义上就是与知识库相关的 **问答**，和微信式「无检索闲聊」不同：回答应 **绑在检索到的片段上**。  
- **多轮连续对话**（带上下文、追问）在本文 **§7** 标为二期：需要会话表与更长的 prompt 管理，**不挡 MVP 上线**。

### 判题、参考答案生成会不会更多靠本地、从而少调模型？

- **判题（`submit` / `daily/submit`）**：**不会**因本功能自动改成「少调模型」。阅卷仍是对「题干 + 你的作答」调用现有 **`call_doubao_grade`**；RAG **不替代** 打分逻辑。若将来要做「对照参考答案要点判分」，那是 **另一条产品需求**，需在阅卷路径里 **显式接入** 检索结果，不在当前 MVP 范围内。  
- **参考答案生成（导入/建题时）**：同样 **不因** Copilot 自动减少；仍由现有 `resolve_reference_for_stem` / 抽取管线负责。  
- **知识库问答（`/api/kb/query`）**：每次有效提问仍会 **至少调用 1 次** 模型做「综合与表述」；**本地负责的是检索**（MySQL FULLTEXT / LIKE），不是省掉生成这一步。相对「不检索、整库塞进 prompt」的做法，RAG 通常能 **缩短上下文、降低胡编概率**，这是主要收益，**不等于**整体 API 调用次数一定下降。  
- **总结**：本步目标是 **「有据可查的问答体验」** 与 **「题库可检索」**；**「全局少调模型」** 已由前序 [todo-reduce-duplicate-ai-calls.md](./todo-reduce-duplicate-ai-calls.md) 等优化承担，二者互补、职责不同。

---

## 0. 前置与决策

| Step | 任务 | 验收 | 状态 |
|------|------|------|------|
| 0.1 | 确认 MySQL 版本与字符集（建议 **8.x** + `utf8mb4`） | 与现有 `DATABASE_URL` 一致 | √ |
| 0.2 | 选定 MVP 检索方案：**FULLTEXT** 为主；若中文分词效果差再保留 **LIKE 降级开关**（配置项或代码分支） | 文档写明取舍 | √ |
| 0.3 | 定义 `chunk` 类型枚举（字符串常量即可） | 例：`question_stem`、`question_reference`；预留 `note` / `import_raw` | √ |

---

## 1. 数据模型与迁移

| Step | 任务 | 验收 | 状态 |
|------|------|------|------|
| 1.1 | 新增 ORM 模型 **`DocumentChunk`**（表名建议 `document_chunks`） | 字段以 `chunk_meta` 存 JSON；其余与清单一致 | √ |
| 1.2 | **`question_id` 外键** 指向 `questions.id`；`ON DELETE CASCADE` 或应用层同步删除策略二选一并在文档说明 | 删题后 chunk 不残留孤儿 | √ |
| 1.3 | Alembic **`revision`** 建表 + **FULLTEXT 索引**（对 `text` 列，或与 `source_type` 组合策略见 MySQL 文档） | `alembic upgrade head` 无报错 | √ |
| 1.4 | （可选）**ngram 解析器** / `ft_min_token_size` 等：若默认 InnoDB 全文对中文不理想，记录调参或改用 `LIKE` MVP | README 或本文「已知问题」 | （可选未做；代码已对 MySQL 空全文结果走 LIKE） |

---

## 2. 写入路径：chunk 同步

| Step | 任务 | 验收 | 状态 |
|------|------|------|------|
| 2.1 | 抽 **`sync_question_chunks(db, question: Question)`** 服务函数 | 删除该题旧 chunks 再插入：stem 一条、非空 `reference_answer` 一条 | √ |
| 2.2 | **`POST /api/questions`**（create）在 `commit` 前 **flush + sync**（与 commit 后等价可搜） | 新题立刻可搜 | √ |
| 2.3 | **`PUT /api/questions/{id}`**（update）在 stem/reference 变更后调用 sync | 更新后检索结果一致 | √ |
| 2.4 | **导入 `import_commit` / `import_commit_one`** 在题目写入成功后调用 sync | 批量导入后可搜 | √ |
| 2.5 | **一次性回填脚本或管理接口**（可选）：`POST /api/kb/reindex` 遍历全表 `questions` 写 chunk | 老数据无需手工点每题 | √ |

---

## 3. 检索层（MVP）

| Step | 任务 | 验收 | 状态 |
|------|------|------|------|
| 3.1 | **`search_chunks(db, query: str, top_k: int) -> list[DocumentChunk]`** | MySQL：`MATCH ... NATURAL LANGUAGE` + 无结果时 **contains/LIKE**；SQLite：contains | √ |
| 3.2 | 空结果处理 | 返回空列表，不抛 500 | √ |
| 3.3 | （可选）**简单 rerank**：同一 `question_id` 多 chunk 合并展示权重 | 同一题 stem+ref 同时命中时去重引用 | （可选未做） |

---

## 4. RAG 生成与 API

| Step | 任务 | 验收 | 状态 |
|------|------|------|------|
| 4.1 | Pydantic：`KbQueryRequest`（`query: str`, `top_k: int` 默认 5）、`KbCitation`、`KbQueryResponse` | OpenAPI 可见 | √ |
| 4.2 | **`POST /api/kb/query`** | 200：`answer`（Markdown 或纯文本）+ `citations[]`（`chunk_id`, `question_id`, `excerpt`, `source_type`） | √ |
| 4.3 | **System + user Prompt**：仅允许使用「上下文片段」作答；无片段时固定短句「知识库中未找到相关条目」 | 人工试「胡编八扯题」不瞎编技术细节 | √ |
| 4.4 | 调用现有 **`call_doubao_extract` 或新增 `call_kb_answer`**（推荐独立函数便于调 `max_output_tokens`） | 已实现 **`call_doubao_kb_query`** + 共享 `_post_doubao_responses_op` | √ |
| 4.5 | **超时 / 与现有 AI 配置一致** | 复用 `AI_TIMEOUT_*`；日志 `ai_call_prepare op=kb_query` | √ |

---

## 5. 前端

| Step | 任务 | 验收 | 状态 |
|------|------|------|------|
| 5.1 | **`frontend/src/api/kb.ts`** | `postKbQuery` 封装 | √ |
| 5.2 | **路由** `/kb` 或 `/copilot` | 已注册 **`/copilot`** | √ |
| 5.3 | **页面**：输入框、发送、展示回答（**MarkdownRenderer**）+ **引用列表**（chunk_id / 题号链接到 `/questions` 或弹窗） | 端到端可走通 | √ |
| 5.4 | **导航入口**（`App.vue` 侧栏或首页卡片） | 用户可发现入口 | √ |

---

## 6. 文档与质量

| Step | 任务 | 验收 | 状态 |
|------|------|------|------|
| 6.1 | 更新 **`docs/api-reference.md`**（`/api/kb/query`、可选 `/api/kb/reindex`） | 与仓库约定一致 | √ |
| 6.2 | 本文 **§0–§5** 全部 `[x]` 后，在 [feature-roadmap-tasks-and-tech.md](./feature-roadmap-tasks-and-tech.md) §2 小项表打勾或写「见 todo-rag-knowledge-copilot」 | 双向可追溯 | √ |
| 6.3 | **pytest**：`search_chunks` 空库 / 单条命中（可用内存或 pytest 文件库） | CI 或本地 `pytest` 通过 | √ |

---

## 7. 二期（可选，不阻塞 MVP）

| Step | 任务 | 说明 |
|------|------|------|
| 7.1 | **向量**：chunk 写入时调火山 **Embedding**；检索时余弦 Top-K + 与 FULLTEXT 融合 | hybrid / RRF |
| 7.2 | **多轮**：`kb_threads`、`kb_messages` 表 + `POST /api/kb/messages` | 上下文只带最近 N 轮 + 本轮检索片段 |
| 7.3 | **SSE**：`GET` 或 `POST` stream 版本 | 与 [ai-latency-and-streaming.md](./ai-latency-and-streaming.md) 对齐 |

---

## 8. 建议实现顺序（与 §1–§5 对应）

1. **§1** 迁移 + 模型（无业务逻辑也可先 `upgrade head`）  
2. **§2** sync 服务 + 接 create/update/import  
3. **§3** 检索函数 + 单元测试  
4. **§4** `POST /api/kb/query` + Prompt  
5. **§5** 前端页 + 导航  
6. **§6** 文档与 pytest  
7. 需要时再开 **§7**

---

## 9. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-05-08 | 初版：RAG Copilot MVP 分阶段 checklist |
| 2026-05-08 | 增补：完成目的与产出；聊天/判题/少调模型之能力边界说明 |
| 2026-05-08 | MVP 已落地：§0–§6 状态列打勾；MySQL 迁移 `r1a2g3c4o5p6` 已执行 |
