<script setup lang="ts">
import { ref } from "vue";
import { commitImport, fetchPromptTemplate, type ImportCommitResponse } from "../api/importing";

const prompt = ref("");
const jsonText = ref(`{
  "questions": []
}`);
const result = ref<ImportCommitResponse | null>(null);
const error = ref("");
const loadingPrompt = ref(false);
const committing = ref(false);

async function loadPrompt() {
  loadingPrompt.value = true;
  error.value = "";
  try {
    const data = await fetchPromptTemplate();
    prompt.value = data.prompt;
  } catch (e) {
    error.value = "获取提示词失败（请先配置分类和岗位）";
  } finally {
    loadingPrompt.value = false;
  }
}

async function submitImport() {
  committing.value = true;
  error.value = "";
  result.value = null;
  try {
    const payload = JSON.parse(jsonText.value);
    result.value = await commitImport(payload);
  } catch (e) {
    error.value = "导入失败，请检查 JSON 格式或字段是否命中本地分类/岗位";
  } finally {
    committing.value = false;
  }
}
</script>

<template>
  <section>
    <h2>AI 导入</h2>
    <p>流程：先点“获取豆包提示词” -> 用提示词调用豆包 -> 粘贴返回 JSON -> 提交入库。</p>

    <div style="display: flex; gap: 8px; margin-bottom: 12px;">
      <button @click="loadPrompt" :disabled="loadingPrompt">
        {{ loadingPrompt ? "加载中..." : "获取豆包提示词" }}
      </button>
      <button @click="submitImport" :disabled="committing">
        {{ committing ? "提交中..." : "提交导入 JSON" }}
      </button>
    </div>

    <p v-if="error" style="color: #c0392b;">{{ error }}</p>

    <h3>提示词模板</h3>
    <textarea v-model="prompt" rows="10" style="width: 100%;" />

    <h3>豆包返回的 JSON</h3>
    <textarea v-model="jsonText" rows="16" style="width: 100%; font-family: Consolas, monospace;" />

    <div v-if="result" style="margin-top: 12px;">
      <h3>导入结果</h3>
      <pre>{{ JSON.stringify(result, null, 2) }}</pre>
    </div>
  </section>
</template>

