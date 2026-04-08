<script setup lang="ts">
import axios from "axios";
import { computed, reactive, ref } from "vue";
import LoadingIndicator from "../components/LoadingIndicator.vue";
import {
  fetchPracticeSummary,
  startPracticeSession,
  submitPracticeAnswer,
  type PracticeSummaryResponse
} from "../api/practice";

const loading = ref(false);
const submitting = ref(false);
const error = ref("");
const sessionId = ref<number | null>(null);
const questions = ref<any[]>([]);
const currentIndex = ref(0);
const answer = ref("");
const perQuestionResult = reactive<Record<number, { score: number; analysis: string; reference: string }>>({});
const summary = ref<PracticeSummaryResponse | null>(null);

const currentQuestion = computed(() => questions.value[currentIndex.value] ?? null);
const finished = computed(() => currentIndex.value >= questions.value.length && questions.value.length > 0);

async function startSession() {
  loading.value = true;
  error.value = "";
  summary.value = null;
  Object.keys(perQuestionResult).forEach((k) => delete perQuestionResult[Number(k)]);
  try {
    const data = await startPracticeSession();
    sessionId.value = data.session_id;
    questions.value = data.questions;
    currentIndex.value = 0;
    answer.value = "";
  } catch (e) {
    if (axios.isAxiosError(e)) error.value = JSON.stringify(e.response?.data?.detail ?? e.message);
    else error.value = String(e);
  } finally {
    loading.value = false;
  }
}

async function submitCurrent() {
  if (!sessionId.value || !currentQuestion.value) return;
  if (!answer.value.trim()) {
    error.value = "请先填写答案";
    return;
  }
  submitting.value = true;
  error.value = "";
  try {
    const data = await submitPracticeAnswer(sessionId.value, currentQuestion.value.id, answer.value.trim());
    perQuestionResult[currentQuestion.value.id] = {
      score: data.record.ai_score,
      analysis: data.analysis,
      reference: data.reference_answer
    };
  } catch (e) {
    if (axios.isAxiosError(e)) error.value = JSON.stringify(e.response?.data?.detail ?? e.message);
    else error.value = String(e);
  } finally {
    submitting.value = false;
  }
}

async function nextQuestion() {
  if (!currentQuestion.value) return;
  if (!perQuestionResult[currentQuestion.value.id]) {
    error.value = "请先提交并完成判题";
    return;
  }
  currentIndex.value += 1;
  answer.value = "";
  error.value = "";
  if (finished.value && sessionId.value) {
    summary.value = await fetchPracticeSummary(sessionId.value);
  }
}
</script>

<template>
  <section>
    <h2>训练中心（每次 10 题）</h2>
    <p v-if="error" style="color: #c0392b;">{{ error }}</p>

    <div
      v-if="!questions.length && !loading"
      class="swift-card"
      style="min-height: 52vh; display: grid; place-items: center;"
    >
      <button @click="startSession">开始刷题</button>
    </div>
    <div v-if="loading" class="swift-card" style="min-height: 200px; display: grid; place-items: center;">
      <LoadingIndicator text="正在准备题目..." />
    </div>

    <div v-if="currentQuestion && !finished" style="margin-top: 14px; border: 1px solid #ddd; padding: 12px;">
      <p>第 {{ currentIndex + 1 }} / {{ questions.length }} 题</p>
      <h3>{{ currentQuestion.stem }}</h3>
      <p>分类：{{ currentQuestion.category }} | 难度：{{ currentQuestion.difficulty }}</p>

      <textarea v-model="answer" rows="6" style="width: 100%;" placeholder="输入你的答案"></textarea>
      <div style="display: flex; gap: 8px; margin-top: 8px;">
        <button @click="submitCurrent" :disabled="submitting">{{ submitting ? "判题中..." : "提交并判题" }}</button>
        <button @click="nextQuestion">下一题</button>
      </div>
      <LoadingIndicator v-if="submitting" text="AI 正在判题..." />

      <div v-if="perQuestionResult[currentQuestion.id]" style="margin-top: 10px; background: #f7fbff; padding: 10px;">
        <p><strong>得分：</strong>{{ perQuestionResult[currentQuestion.id].score }} / 10</p>
        <p><strong>解析：</strong>{{ perQuestionResult[currentQuestion.id].analysis }}</p>
        <p><strong>参考答案：</strong>{{ perQuestionResult[currentQuestion.id].reference || "-" }}</p>
      </div>
    </div>

    <div v-if="finished && summary" style="margin-top: 14px; border: 1px solid #ddd; padding: 12px;">
      <h3>本轮完成</h3>
      <p><strong>总分：</strong>{{ summary.total_score }} / 100</p>
      <p><strong>记录ID：</strong>{{ summary.record_ids.join(", ") }}</p>
      <p><strong>会话ID：</strong>{{ summary.session_id }}</p>
    </div>
  </section>
</template>

