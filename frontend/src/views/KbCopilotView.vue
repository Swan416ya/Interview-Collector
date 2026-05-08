<script setup lang="ts">
import axios from "axios";
import { ref } from "vue";
import LoadingIndicator from "../components/LoadingIndicator.vue";
import MarkdownRenderer from "../components/MarkdownRenderer.vue";
import { postKbQuery, postKbReindex, type KbCitation, type KbQueryResponse } from "../api/kb";

const query = ref("");
const loading = ref(false);
const reindexing = ref(false);
const error = ref("");
const errorDetail = ref("");
const infoMessage = ref("");
const last = ref<KbQueryResponse | null>(null);

function formatError(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") {
      errorDetail.value = detail;
      return fallback;
    }
    if (detail !== undefined) {
      errorDetail.value = JSON.stringify(detail, null, 2);
      return fallback;
    }
    if (err.message) {
      errorDetail.value = err.message;
      return fallback;
    }
  }
  errorDetail.value = String(err ?? "");
  return fallback;
}

async function runQuery() {
  const q = query.value.trim();
  if (!q) {
    error.value = "请输入问题";
    errorDetail.value = "";
    return;
  }
  loading.value = true;
  error.value = "";
  errorDetail.value = "";
  infoMessage.value = "";
  last.value = null;
  try {
    last.value = await postKbQuery(q, 5);
  } catch (e) {
    error.value = formatError(e, "查询失败");
  } finally {
    loading.value = false;
  }
}

async function runReindex() {
  reindexing.value = true;
  error.value = "";
  errorDetail.value = "";
  infoMessage.value = "";
  try {
    const r = await postKbReindex();
    infoMessage.value = `已重建索引：处理 ${r.questions_processed} 道题目。`;
  } catch (e) {
    error.value = formatError(e, "重建索引失败");
  } finally {
    reindexing.value = false;
  }
}

function sourceLabel(c: KbCitation): string {
  if (c.source_type === "question_stem") return "题干";
  if (c.source_type === "question_reference") return "参考答案";
  return c.source_type;
}

function onQueryKeydown(e: KeyboardEvent) {
  if (e.key === "Enter" && e.ctrlKey) {
    e.preventDefault();
    void runQuery();
  }
}
</script>

<template>
  <section>
    <h2>知识库 Copilot</h2>
    <p>
      在已入库题目的<strong>题干与参考答案</strong>中检索相关片段，并由 AI
      综合回答；回答下方列出引用片段，便于回到题库核对。
    </p>

    <p v-if="error" style="color: #c0392b;">{{ error }}</p>
    <p v-if="infoMessage" style="color: #1a7f37;">{{ infoMessage }}</p>
    <pre
      v-if="errorDetail"
      style="white-space: pre-wrap; background: #fff5f5; border: 1px solid #ffd7d7; padding: 10px; border-radius: 6px;"
    >{{ errorDetail }}</pre>

    <div style="margin-top: 12px; display: flex; flex-direction: column; gap: 10px;">
      <textarea
        v-model="query"
        rows="4"
        style="width: 100%; font-family: inherit;"
        placeholder="用自然语言提问，例如：Redis 持久化怎么做？"
        @keydown="onQueryKeydown"
      />
      <div style="display: flex; gap: 8px; flex-wrap: wrap;">
        <button type="button" :disabled="loading" @click="runQuery">
          {{ loading ? "检索并生成中…" : "提问" }}
        </button>
        <button type="button" :disabled="reindexing" @click="runReindex">
          {{ reindexing ? "重建中…" : "重建全库索引" }}
        </button>
      </div>
      <p style="font-size: 13px; color: #6b7280; margin: 0;">
        提示：Ctrl+Enter 提交。首次使用旧数据可点「重建全库索引」。
      </p>
    </div>

    <LoadingIndicator v-if="loading" text="正在检索知识库并调用 AI（约 10–60 秒）…" />

    <div v-if="last" style="margin-top: 20px;">
      <h3>回答</h3>
      <div
        style="border: 1px solid #e3e8f2; border-radius: 10px; padding: 12px; background: #fafbff;"
      >
        <MarkdownRenderer :source="last.answer" />
      </div>

      <h3 style="margin-top: 16px;">引用</h3>
      <p v-if="!last.citations.length" style="color: #6b7280;">无片段引用（例如未命中知识库）。</p>
      <ul v-else style="padding-left: 18px; margin: 0;">
        <li v-for="c in last.citations" :key="c.chunk_id" style="margin-bottom: 10px;">
          <div style="font-size: 13px; color: #374151;">
            <strong>{{ sourceLabel(c) }}</strong>
            · chunk #{{ c.chunk_id }}
            ·
            <router-link :to="{ name: 'questions' }">去题库查找题目 #{{ c.question_id }}</router-link>
          </div>
          <div
            style="margin-top: 4px; font-size: 13px; color: #4b5563; white-space: pre-wrap;"
          >{{ c.excerpt }}</div>
        </li>
      </ul>
    </div>
  </section>
</template>
