# AI 延迟体感与流式输出（说明）

本文说明：为什么常见请求要等 **十几秒**、**不流式**时前端能做什么、若要做真流式需要哪些条件。

---

## 1. 延迟从哪里来

| 因素 | 说明 |
|------|------|
| 模型推理 | 云端排队 + 生成长度；`max_output_tokens` 越大，尾部延迟往往越高。 |
| 网络 RTT | 客户端 → 你的 FastAPI → 火山 Ark，多一跳 TLS。 |
| 任务形态 | **结构化 JSON**（抽取、阅卷）必须等模型**输出完整**再解析；中途片段往往不是合法 JSON，无法当「半道题」展示。 |
| 深度思考 | 若 Endpoint 开启 thinking，首 token 会更晚；本项目默认 `AI_THINKING_TYPE=disabled`（见 `.env.example`）。 |

**已做的减负（不改变模型）**：见 [todo-reduce-duplicate-ai-calls.md](./todo-reduce-duplicate-ai-calls.md)（参考答案复用、预览 chunk 缓存、daily 阅卷短时幂等）。

---

## 2. 「生成一点就渲染一点」是否可行

**可以，但有前提：**

- **火山方舟**对 **Responses API / Chat** 提供 **流式（SSE）** 能力（官方文档检索「流式响应」「流式输出」）。  
- 当前仓库的 `ai_service.py` 使用 **`POST .../responses` + 整包 JSON**，是**非流式**路径；要流式需改请求体（如 `stream: true`，以你控制台/API 文档为准）并用 **SSE 客户端**边读边解析事件。
- **阅卷 / 抽取**：业务要的是 **完整 JSON**；流式阶段用户看到的是 **自然语言 token**，直到结束才能稳定 `json.loads`。体感上可以「打字机展示思考过程」，但**分数与入库仍须在流结束后**才能确定。
- **参考答案长文本**：最适合做流式展示（用户逐字看到解析）；仍要处理 provider 事件格式与错误恢复。

**结论**：  
- **想明显省总时间**：主要靠 **更短输出**、**缓存**、**换更快 Endpoint**（你已用 seed lite），流式**不减少**总 token 生成时间，只改善**首字等待**。  
- **想改善体感**：流式 **或** 前端加强「预计等待 + 动画 + 分步文案」（实现成本低）。

---

## 3. 本项目内低成本体感优化（推荐优先）

| 手段 | 成本 | 效果 |
|------|------|------|
| 按钮旁固定提示「约 10–30 秒」 | 极低 | 降低焦虑、减少重复点击 |
| `LoadingIndicator` 分阶段文案 | 低 | 已部分用于练习判题 / 导入 |
| 保持 `axios`/`fetch` 较长 `timeout` | 已有 | 避免误判失败 |
| 后续：仅对「参考答案」接流式端点 + 新路由 `GET .../stream` | 中 | 长文体验最好 |

---

## 4. 若以后做真流式（实现清单草案）

1. 查当前 Endpoint 在火山文档中 **Responses 流式** 的字段名与事件 shape。  
2. `httpx` 使用 `client.stream("POST", ...)` 或 SSE 库消费 `text/event-stream`。  
3. FastAPI `StreamingResponse` 将字节/事件转发给浏览器；前端 `EventSource` 或 `fetch` + `ReadableStream`。  
4. **结构化接口**旁路保留非流式版本，便于对比与降级。

---

## 5. 相关文档

- [ai-doubao-integration.md](./ai-doubao-integration.md) — 当前 Ark 调用形态  
- [feature-roadmap-tasks-and-tech.md §2](./feature-roadmap-tasks-and-tech.md) — RAG 阶段可规划 SSE  

---

## 修订记录

| 日期 | 说明 |
|------|------|
| 2026-05-08 | 初版：延迟来源、流式可行性、体感优化与后续清单 |
