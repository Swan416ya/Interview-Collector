<script setup lang="ts">
import axios from "axios";
import { computed, ref, watch } from "vue";
import LoadingIndicator from "../components/LoadingIndicator.vue";
import MarkdownRenderer from "../components/MarkdownRenderer.vue";
import { addWrongbookManual, fetchWrongbookPage, type WrongbookPage } from "../api/practice";

type StateTab = "in" | "out" | "all";

const state = ref<StateTab>("in");
const page = ref(1);
const pageSize = ref(20);
const loading = ref(false);
const error = ref("");
const data = ref<WrongbookPage | null>(null);
const manualId = ref("");
const manualBusy = ref(false);
const expandedId = ref<number | null>(null);

const totalPages = computed(() => {
  const t = data.value?.total ?? 0;
  return Math.max(1, Math.ceil(t / pageSize.value));
});

async function load() {
  loading.value = true;
  error.value = "";
  try {
    data.value = await fetchWrongbookPage({
      state: state.value,
      page: page.value,
      page_size: pageSize.value
    });
  } catch (e) {
    error.value = axios.isAxiosError(e)
      ? JSON.stringify(e.response?.data?.detail ?? e.message)
      : String(e);
    data.value = null;
  } finally {
    loading.value = false;
  }
}

async function manualAdd() {
  const id = Number(manualId.value.trim());
  if (!Number.isFinite(id) || id < 1) {
    error.value = "请输入有效题目 ID";
    return;
  }
  manualBusy.value = true;
  error.value = "";
  try {
    await addWrongbookManual(id);
    manualId.value = "";
    await load();
  } catch (e) {
    error.value = axios.isAxiosError(e)
      ? JSON.stringify(e.response?.data?.detail ?? e.message)
      : String(e);
  } finally {
    manualBusy.value = false;
  }
}

watch(
  [state, page, pageSize],
  () => {
    void load();
  },
  { immediate: true }
);
</script>

<template>
  <section>
    <h2>错题本</h2>
    <p style="font-size: 14px; color: #4b5563; max-width: 52rem;">
      在练：<strong>当前在错题本</strong>（可去训练中心选「仅错题本」开刷）。曾移出：有过准出时间、已不再算作错题。全部：曾经进过错题本的题目。
      规则默认：单次 AI 分 ≤6（或跳过记 0 分）准入；最近连续 3 次作答均 ≥8 分准出（可在后端 <code>WRONGBOOK_*</code> 调整）。
    </p>

    <div style="display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 12px 0;">
      <button type="button" @click="state = 'in'; page = 1">在练</button>
      <button type="button" @click="state = 'out'; page = 1">已准出</button>
      <button type="button" @click="state = 'all'; page = 1">全部曾入本</button>
    </div>

    <div
      style="display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 12px; padding: 10px; border-radius: 8px; border: 1px solid #e5e7eb;"
    >
      <span style="font-size: 14px;">手动加入题目 ID：</span>
      <input v-model="manualId" type="text" inputmode="numeric" placeholder="例如 42" style="width: 100px;" />
      <button type="button" :disabled="manualBusy" @click="manualAdd">{{ manualBusy ? "…" : "加入错题本" }}</button>
    </div>

    <p v-if="error" style="color: #c0392b;">{{ error }}</p>

    <LoadingIndicator v-if="loading" text="加载中…" />

    <template v-else-if="data">
      <p style="font-size: 14px; color: #6b7280;">
        共 {{ data.total }} 条 · 第 {{ page }} / {{ totalPages }} 页
      </p>
      <div v-if="!data.items.length" style="padding: 24px; color: #6b7280;">暂无数据。</div>
      <ul v-else style="list-style: none; padding: 0; margin: 0; display: grid; gap: 10px;">
        <li
          v-for="q in data.items"
          :key="q.id"
          style="border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px; background: #fafafa;"
        >
          <div style="display: flex; flex-wrap: wrap; gap: 8px; align-items: baseline;">
            <strong>#{{ q.id }}</strong>
            <span style="font-size: 13px; color: #6b7280;">{{ q.category }} · 难度 {{ q.difficulty }}</span>
            <span
              v-if="q.wrongbook_active"
              style="font-size: 12px; padding: 2px 8px; border-radius: 999px; background: #fee2e2; color: #991b1b;"
            >在练</span>
            <span
              v-else-if="q.wrongbook_cleared_at"
              style="font-size: 12px; padding: 2px 8px; border-radius: 999px; background: #d1fae5; color: #065f46;"
            >已准出</span>
            <router-link :to="{ name: 'questions' }" style="font-size: 13px;">去题库查看</router-link>
            <button type="button" style="font-size: 13px;" @click="expandedId = expandedId === q.id ? null : q.id">
              {{ expandedId === q.id ? "收起" : "展开题干" }}
            </button>
          </div>
          <div v-if="expandedId === q.id" style="margin-top: 8px;">
            <MarkdownRenderer :source="q.stem" />
          </div>
        </li>
      </ul>
      <div v-if="totalPages > 1" style="margin-top: 16px; display: flex; gap: 8px; align-items: center;">
        <button type="button" :disabled="page <= 1" @click="page -= 1">上一页</button>
        <button type="button" :disabled="page >= totalPages" @click="page += 1">下一页</button>
      </div>
    </template>
  </section>
</template>
