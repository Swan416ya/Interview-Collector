<script setup lang="ts">
import axios from "axios";
import { ref } from "vue";
import {
  commitImport,
  previewImport,
  type ImportCommitResponse,
  type PreviewQuestionItem
} from "../api/importing";

const rawText = ref("");
const previewItems = ref<PreviewQuestionItem[]>([]);
const selected = ref<boolean[]>([]);
const result = ref<ImportCommitResponse | null>(null);
const error = ref("");
const errorDetail = ref("");
const previewing = ref(false);
const committing = ref(false);

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

async function runPreview() {
  if (rawText.value.trim().length < 10) {
    error.value = "请输入更完整的面经原文";
    errorDetail.value = "";
    return;
  }
  previewing.value = true;
  error.value = "";
  errorDetail.value = "";
  result.value = null;
  try {
    const data = await previewImport(rawText.value.trim());
    previewItems.value = data.questions;
    selected.value = data.questions.map(() => true);
  } catch (e) {
    error.value = formatError(e, "提取失败，请看下方详细错误");
  } finally {
    previewing.value = false;
  }
}

async function submitImport() {
  const checkedQuestions = previewItems.value.filter((_, idx) => selected.value[idx]);
  if (!checkedQuestions.length) {
    error.value = "请至少勾选一题再导入";
    errorDetail.value = "";
    return;
  }
  committing.value = true;
  error.value = "";
  errorDetail.value = "";
  result.value = null;
  try {
    result.value = await commitImport({ questions: checkedQuestions });
  } catch (e) {
    error.value = formatError(e, "导入失败，请看下方详细错误");
  } finally {
    committing.value = false;
  }
}

function toggleAll(checked: boolean) {
  selected.value = previewItems.value.map(() => checked);
}
</script>

<template>
  <section>
    <h2>AI 导入</h2>
    <p>流程：粘贴面经原文 -> 后端调用豆包提取 -> 勾选题目（默认全选）-> 导入。</p>

    <div style="display: flex; gap: 8px; margin-bottom: 12px;">
      <button @click="runPreview" :disabled="previewing">
        {{ previewing ? "提取中..." : "1) AI 提取预览" }}
      </button>
      <button @click="submitImport" :disabled="committing">
        {{ committing ? "导入中..." : "2) 导入勾选题目" }}
      </button>
      <button @click="toggleAll(true)">全选</button>
      <button @click="toggleAll(false)">全不选</button>
    </div>

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

    <h3 style="margin-top: 16px;">提取结果（默认全选）</h3>
    <p v-if="!previewItems.length">暂无提取结果，请先点击“AI 提取预览”。</p>
    <div v-else style="display: grid; gap: 10px;">
      <label
        v-for="(item, idx) in previewItems"
        :key="idx"
        style="display: block; border: 1px solid #ddd; padding: 10px; border-radius: 6px;"
      >
        <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 6px;">
          <input v-model="selected[idx]" type="checkbox" />
          <strong>题目 {{ idx + 1 }}</strong>
        </div>
        <div><strong>题干：</strong>{{ item.stem }}</div>
        <div><strong>分类：</strong>{{ item.category_name }}</div>
        <div><strong>岗位：</strong>{{ item.roles?.join("、") || "-" }}</div>
        <div><strong>公司：</strong>{{ item.companies?.join("、") || "-" }}</div>
        <div><strong>难度：</strong>{{ item.difficulty }}</div>
      </label>
    </div>

    <div v-if="result" style="margin-top: 12px;">
      <h3>导入结果</h3>
      <pre>{{ JSON.stringify(result, null, 2) }}</pre>
    </div>
  </section>
</template>

