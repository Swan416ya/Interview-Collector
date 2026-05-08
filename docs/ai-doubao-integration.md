# Doubao (Volcengine Ark) Integration Guide

## 0. Latency and streaming

See [ai-latency-and-streaming.md](./ai-latency-and-streaming.md) for why calls can take 10–30s, UX mitigations, and when true SSE streaming would require API changes.

## 1. Environment Variables

Set in `backend/.env`:

```env
AI_PROVIDER=openai_compatible
AI_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
AI_MODEL=your_ark_endpoint_id
AI_API_KEY=your_ark_api_key
```

Notes:

- `AI_MODEL` should use your Ark endpoint/deployment id.
- Keep `AI_API_KEY` private and never commit it.

## 2. Python Call Pattern (OpenAI-Compatible)

Example using `openai` SDK style:

```python
from openai import OpenAI

client = OpenAI(
    api_key=AI_API_KEY,
    base_url=AI_BASE_URL,
)

resp = client.chat.completions.create(
    model=AI_MODEL,
    messages=[
        {"role": "system", "content": "You are a strict JSON extractor."},
        {"role": "user", "content": "..."}, 
    ],
    temperature=0.1,
)
```

## 3. Prompt Template: Interview Text -> Structured Questions

### Extraction System Prompt

```text
你是一个面试题结构化提取器。你只能输出 JSON，不能输出任何额外解释。
请将输入的面经文本拆分为多道题，并标准化分类。
```

### Extraction User Prompt Template

```text
请从下面文本中提取题目，输出为 JSON，格式必须严格为：
{
  "questions": [
    {
      "stem": "string",
      "category_name": "操作系统|计算机网络|数据库|Java|前端|后端|测试|其他",
      "companies": ["string"],
      "roles": ["前端|后端|客户端|测试|算法|其他"],
      "difficulty": 1-5,
      "answer_reference": "string",
      "confidence": 0-1
    }
  ]
}

要求：
1) 只输出 JSON；
2) 不要遗漏题目；
3) 同义分类统一到标准分类；
4) 无法判断的字段按合理默认值填写。

面经文本：
{{raw_text}}
```

## 4. Prompt Template: AI Grading

### Grading System Prompt

```text
你是严格的计算机面试官。请基于评分维度给出结构化评分结果，只输出 JSON。
```

### Grading User Prompt Template

```text
请对用户答案评分并输出 JSON，格式：
{
  "score": 0-100,
  "dimensions": {
    "accuracy": 0-100,
    "completeness": 0-100,
    "logic": 0-100,
    "terminology": 0-100
  },
  "strengths": ["string"],
  "gaps": ["string"],
  "suggestions": ["string"]
}

题目：
{{question}}

参考答案：
{{reference_answer}}

用户答案：
{{user_answer}}
```

## 5. Reliability Recommendations

- Use low temperature (`0.0~0.2`) for extraction and grading.
- Validate output with Pydantic schema.
- If parse fails, run one repair pass; if still fails, record as failed item.

## 6. Official References

- [火山方舟快速开始](https://www.volcengine.com/docs/82379/1928261)
- [火山方舟文档入口](https://www.volcengine.com/docs/82379/1099455)
- [火山方舟 OpenViking 页面](https://www.volcengine.com/docs/82379/2288685)
