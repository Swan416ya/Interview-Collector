<script setup lang="ts">
import axios from "axios";
import { ref } from "vue";
import LoadingIndicator from "../components/LoadingIndicator.vue";
import MarkdownRenderer from "../components/MarkdownRenderer.vue";
import {
  commitImportOne,
  previewImport,
  type ImportRowStatus,
  type PreviewQuestionItem
} from "../api/importing";

const rawText = ref("");
const previewItems = ref<PreviewQuestionItem[]>([]);
const selected = ref<boolean[]>([]);
const rowStatus = ref<ImportRowStatus[]>([]);
const savedQuestionId = ref<(number | null)[]>([]);
const importSummary = ref<{ ok: number; err: number } | null>(null);
const error = ref("");
const errorDetail = ref("");
const previewing = ref(false);
/** 最近一次预览的抽取缓存统计（后端 extract_cache_*） */
const previewCacheHint = ref("");
const committing = ref(false);
const currentImportIndex = ref(0);
const currentImportTotal = ref(0);

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

function rowBoxClass(idx: number): string {
  const st = rowStatus.value[idx] ?? "idle";
  if (st === "ok") return "import-row import-row--ok";
  if (st === "err") return "import-row import-row--err";
  if (st === "loading") return "import-row import-row--loading";
  return "import-row";
}

async function runPreview() {
  if (rawText.value.trim().length < 10) {
    error.value = "请输入更完整的面经原文";
    errorDetail.value = "";
    return;
  }
  previewing.value = true;
  error.value = "";
  errorDetail.value = "";
  importSummary.value = null;
  previewCacheHint.value = "";
  try {
    const data = await previewImport(rawText.value.trim());
    const hits = data.extract_cache_hits;
    const misses = data.extract_cache_misses;
    if (typeof hits === "number" && typeof misses === "number") {
      previewCacheHint.value =
        hits > 0
          ? `抽取缓存命中 ${hits} 个分段，实际调用 AI ${misses} 次（相同原文重复预览可省钱）。`
          : `未命中抽取缓存，实际调用 AI ${misses} 次。`;
    }
    previewItems.value = data.questions;
    selected.value = data.questions.map(() => true);
    rowStatus.value = data.questions.map(() => "idle" as ImportRowStatus);
    savedQuestionId.value = data.questions.map(() => null);
  } catch (e) {
    error.value = formatError(e, "提取失败，请看下方详细错误");
  } finally {
    previewing.value = false;
  }
}

async function submitImport() {
  const indices = previewItems.value
    .map((_, i) => i)
    .filter((i) => selected.value[i] && rowStatus.value[i] !== "ok");

  if (!indices.length) {
    const anyOk = rowStatus.value.some((s) => s === "ok");
    error.value = anyOk
      ? "所选题目均已入库，或请勾选尚未入库的题目"
      : "请至少勾选一题再导入";
    errorDetail.value = "";
    return;
  }

  committing.value = true;
  error.value = "";
  errorDetail.value = "";
  importSummary.value = null;
  currentImportTotal.value = indices.length;
  let ok = 0;
  let err = 0;

  try {
    for (let n = 0; n < indices.length; n += 1) {
      const idx = indices[n];
      currentImportIndex.value = n + 1;
      rowStatus.value[idx] = "loading";
      try {
        const res = await commitImportOne(previewItems.value[idx]);
        rowStatus.value[idx] = "ok";
        savedQuestionId.value[idx] = res.id;
        ok += 1;
      } catch (e) {
        rowStatus.value[idx] = "err";
        err += 1;
        formatError(e, `第 ${idx + 1} 题入库失败`);
        error.value = `部分题目失败（已成功 ${ok}，失败 ${err}），最后一条错误见下方`;
      }
    }
    importSummary.value = { ok, err };
  } finally {
    committing.value = false;
    currentImportIndex.value = 0;
    currentImportTotal.value = 0;
  }
}

function toggleAll(checked: boolean) {
  selected.value = previewItems.value.map(() => checked);
}
</script>

<template>
  <section>
    <h2>AI 导入</h2>
    <p>
      流程：粘贴面经原文 → 解析预览 → 勾选题目 →
      <strong>按题逐个</strong>生成参考答案并入库；每成功一题该卡片会标绿，避免某一题 AI 失败导致前面白跑。
    </p>

    <p v-if="error" style="color: #c0392b;">{{ error }}</p>
    <pre
      v-if="errorDetail"
      style="white-space: pre-wrap; background: #fff5f5; border: 1px solid #ffd7d7; padding: 10px; border-radius: 6px;"
    >{{ errorDetail }}</pre>

    <h3>面经原文输入</h3>
    <textarea
      v-model="rawText"
      rows="10"
      style="width: 100%; font-family: Consolas, monospace;"
      placeholder="把 nowcoder 面经原文粘贴到这里"
    />
    <div style="margin-top: 10px; display: flex; gap: 8px;">
      <button @click="runPreview" :disabled="previewing">{{ previewing ? "解析中..." : "解析" }}</button>
      <button @click="toggleAll(true)" :disabled="!previewItems.length">全选</button>
      <button @click="toggleAll(false)" :disabled="!previewItems.length">全不选</button>
    </div>
    <LoadingIndicator v-if="previewing" text="AI 正在解析原文..." />
    <p
      v-if="previewCacheHint"
      style="margin-top: 8px; color: #555; font-size: 14px;"
    >
      {{ previewCacheHint }}
    </p>

    <h3 style="margin-top: 16px;">提取结果（默认全选）</h3>
    <p v-if="!previewItems.length">暂无提取结果，请先点击“AI 提取预览”。</p>
    <div v-else style="display: grid; gap: 10px;">
      <label v-for="(item, idx) in previewItems" :key="idx" :class="rowBoxClass(idx)">
        <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 6px; flex-wrap: wrap;">
          <input v-model="selected[idx]" type="checkbox" :disabled="rowStatus[idx] === 'loading'" />
          <strong>题目 {{ idx + 1 }}</strong>
          <span v-if="rowStatus[idx] === 'ok'" class="import-badge import-badge--ok">
            已入库 #{{ savedQuestionId[idx] }}
          </span>
          <span v-else-if="rowStatus[idx] === 'loading'" class="import-badge import-badge--loading">入库中…</span>
          <span v-else-if="rowStatus[idx] === 'err'" class="import-badge import-badge--err">失败（可重试）</span>
        </div>
        <div>
          <strong>题干：</strong>
          <MarkdownRenderer v-if="item.stem?.trim()" :source="item.stem" />
          <span v-else>-</span>
        </div>
        <div><strong>分类：</strong>{{ item.category_name }}</div>
        <div><strong>岗位：</strong>{{ item.roles?.join("、") || "-" }}</div>
        <div><strong>公司：</strong>{{ item.companies?.join("、") || "-" }}</div>
        <div><strong>难度：</strong>{{ item.difficulty }}</div>
      </label>
    </div>

    <div v-if="importSummary" style="margin-top: 12px; margin-bottom: 68px;">
      <h3>本轮导入汇总</h3>
      <p style="font-size: 14px;">
        成功 <strong style="color: #1a7f37;">{{ importSummary.ok }}</strong> 道，
        失败 <strong style="color: #cf222e;">{{ importSummary.err }}</strong> 道。
      </p>
    </div>

    <div
      style="position: sticky; bottom: 0; z-index: 20; margin-top: 12px; padding: 10px; border-radius: 12px; border: 1px solid #e3e8f2; background: rgba(255,255,255,0.95); backdrop-filter: blur(10px);"
    >
      <button @click="submitImport" :disabled="committing || !previewItems.length">
        {{ committing ? "正在逐题导入…" : "逐个导入勾选题目（未入库）" }}
      </button>
      <LoadingIndicator
        v-if="committing && currentImportTotal > 0"
        :text="`正在导入第 ${currentImportIndex} / ${currentImportTotal} 题…`"
      />
    </div>
  </section>
</template>

<style scoped>
.import-row {
  display: block;
  border: 2px solid #d0d7de;
  padding: 10px;
  border-radius: 8px;
  background: #ffffff;
}

.import-row--ok {
  border-color: #2ea043;
  background: #dcffe4;
  box-shadow: 0 0 0 1px rgba(46, 160, 67, 0.2);
}

.import-row--err {
  border-color: #cf222e;
  background: #fff5f5;
}

.import-row--loading {
  border-color: #0969da;
  background: #f6f8fa;
}

.import-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
}

.import-badge--ok {
  background: #2ea043;
  color: #fff;
}

.import-badge--loading {
  background: #0969da;
  color: #fff;
}

.import-badge--err {
  background: #cf222e;
  color: #fff;
}
</style>
