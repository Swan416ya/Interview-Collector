<script setup lang="ts">
import { onMounted, ref } from "vue";
import {
  fetchPracticeSessionRecords,
  fetchPracticeSessions,
  type PracticeRecord,
  type PracticeSessionListItem
} from "../api/practice";

const sessions = ref<PracticeSessionListItem[]>([]);
const selectedSessionId = ref<number | null>(null);
const selectedRecords = ref<PracticeRecord[]>([]);
const selectedTotal = ref(0);
const loading = ref(false);
const error = ref("");

async function loadSessions() {
  loading.value = true;
  error.value = "";
  try {
    sessions.value = await fetchPracticeSessions();
  } catch (e) {
    error.value = "加载刷题记录失败";
  } finally {
    loading.value = false;
  }
}

async function openSession(sessionId: number) {
  selectedSessionId.value = sessionId;
  const data = await fetchPracticeSessionRecords(sessionId);
  selectedRecords.value = data.records;
  selectedTotal.value = data.total_score;
}

onMounted(loadSessions);
</script>

<template>
  <section>
    <h2>刷题记录</h2>
    <p v-if="error" style="color: #c0392b;">{{ error }}</p>
    <p v-if="loading">加载中...</p>

    <div v-else style="display: grid; grid-template-columns: 320px 1fr; gap: 12px;">
      <div style="border: 1px solid #ddd; padding: 10px;">
        <h3>历史轮次</h3>
        <div v-if="!sessions.length">暂无已完成刷题记录</div>
        <button
          v-for="s in sessions"
          :key="s.id"
          @click="openSession(s.id)"
          style="display: block; width: 100%; text-align: left; margin-bottom: 8px;"
        >
          #{{ s.id }} - {{ s.total_score }}/100
        </button>
      </div>

      <div style="border: 1px solid #ddd; padding: 10px;">
        <h3>轮次详情</h3>
        <div v-if="!selectedSessionId">请选择左侧一条刷题记录</div>
        <div v-else>
          <p><strong>Session：</strong>{{ selectedSessionId }}</p>
          <p><strong>总分：</strong>{{ selectedTotal }}/100</p>
          <div style="max-height: 56vh; overflow: auto; display: grid; gap: 8px;">
            <div v-for="r in selectedRecords" :key="r.id" style="border: 1px solid #eee; padding: 8px;">
              <div><strong>Record #{{ r.id }}</strong> | 评分：{{ r.ai_score }}/10</div>
              <div><strong>用户答案：</strong>{{ r.user_answer || "-" }}</div>
              <div><strong>AI解析：</strong>{{ r.ai_answer || "-" }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

