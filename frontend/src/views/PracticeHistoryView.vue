<script setup lang="ts">
import { onMounted, ref } from "vue";
import MarkdownRenderer from "../components/MarkdownRenderer.vue";
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
const selectedQuestionCount = ref(10);
const selectedCompletedAt = ref("");
const loading = ref(false);
const error = ref("");
const detailVisible = ref(false);

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
  try {
    selectedSessionId.value = sessionId;
    const data = await fetchPracticeSessionRecords(sessionId);
    selectedRecords.value = data.records;
    selectedTotal.value = data.total_score;
    selectedQuestionCount.value = data.question_count ?? 10;
    selectedCompletedAt.value = sessions.value.find((s) => s.id === sessionId)?.completed_at ?? "";
    detailVisible.value = true;
  } catch (e) {
    error.value = "加载会话详情失败";
  }
}

onMounted(loadSessions);
</script>

<template>
  <section>
    <h2>刷题记录</h2>
    <p v-if="error" style="color: #c0392b;">{{ error }}</p>
    <p v-if="loading">加载中...</p>

    <div v-else style="display: grid; gap: 10px;">
      <div v-if="!sessions.length" class="swift-card">暂无已完成刷题记录</div>
      <div
        v-for="s in sessions"
        :key="s.id"
        class="swift-card"
        style="display: flex; justify-content: space-between; align-items: center; gap: 12px;"
      >
        <div>
          <div style="font-weight: 700;">
            总分：{{ s.total_score }}/{{ (s.question_count ?? 10) * 10 }}
          </div>
          <div style="font-size: 12px; color: #667085; margin-top: 4px;">时间：{{ s.completed_at }}</div>
        </div>
        <button @click="openSession(s.id)">查看详情</button>
      </div>
    </div>

    <teleport to="body">
      <div
        v-if="detailVisible && selectedSessionId"
        style="position: fixed; inset: 0; z-index: 1200; background: rgba(17,24,39,0.36); display: grid; place-items: center;"
      >
        <div class="swift-card" style="width: 920px; max-width: 95vw; max-height: 88vh; overflow: auto;">
          <h3 style="margin-top: 0;">刷题详情</h3>
          <p><strong>会话：</strong>#{{ selectedSessionId }}</p>
          <p><strong>总分：</strong>{{ selectedTotal }}/{{ selectedQuestionCount * 10 }}</p>
          <p><strong>时间：</strong>{{ selectedCompletedAt }}</p>
          <div style="max-height: 54vh; overflow: auto; display: grid; gap: 8px;">
            <div v-for="r in selectedRecords" :key="r.id" style="border: 1px solid #dce3ef; padding: 10px; border-radius: 10px;">
              <div><strong>评分：</strong>{{ r.ai_score }}/10</div>
              <div><strong>用户答案：</strong>{{ r.user_answer || "-" }}</div>
              <div>
                <strong>AI 解析：</strong>
                <MarkdownRenderer v-if="r.ai_answer?.trim()" :source="r.ai_answer" />
                <span v-else>-</span>
              </div>
            </div>
          </div>
          <div style="margin-top: 10px;">
            <button @click="detailVisible = false">关闭</button>
          </div>
        </div>
      </div>
    </teleport>
  </section>
</template>

