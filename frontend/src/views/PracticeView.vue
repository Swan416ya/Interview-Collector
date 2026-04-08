<script setup lang="ts">
import axios from "axios";
import { computed, onMounted, reactive, ref } from "vue";
import LoadingIndicator from "../components/LoadingIndicator.vue";
import { fetchQuestions, type Question } from "../api/questions";
import {
  fetchPracticeCategories,
  fetchPracticeSummary,
  skipPracticeAnswer,
  startPracticeSession,
  startPracticeSessionCustom,
  submitPracticeAnswer,
  type PracticeCategoryOption,
  type PracticeSummaryResponse
} from "../api/practice";

type TrainMode = "practice" | "memorize";

const mode = ref<TrainMode>("practice");
const categoryOptions = ref<PracticeCategoryOption[]>([]);
const selectedCategory = ref("");

const loading = ref(false);
const submitting = ref(false);
const error = ref("");

const sessionId = ref<number | null>(null);
const questions = ref<Question[]>([]);
const currentIndex = ref(0);
const answer = ref("");
const perQuestionResult = reactive<Record<number, { score: number; analysis: string; reference: string }>>({});
const summary = ref<PracticeSummaryResponse | null>(null);

const memorizeQuestions = ref<Question[]>([]);
const memorizeIndex = ref(0);
const memorizePrepared = ref(false);

const currentQuestion = computed(() => questions.value[currentIndex.value] ?? null);
const finished = computed(() => currentIndex.value >= questions.value.length && questions.value.length > 0);
const currentMemorizeQuestion = computed(() => memorizeQuestions.value[memorizeIndex.value] ?? null);

function shuffle<T>(arr: T[]): T[] {
  const copied = [...arr];
  for (let i = copied.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    const t = copied[i];
    copied[i] = copied[j];
    copied[j] = t;
  }
  return copied;
}

function clearPracticeState() {
  sessionId.value = null;
  questions.value = [];
  currentIndex.value = 0;
  answer.value = "";
  summary.value = null;
  Object.keys(perQuestionResult).forEach((k) => delete perQuestionResult[Number(k)]);
}

async function loadCategories() {
  categoryOptions.value = await fetchPracticeCategories();
  if (!selectedCategory.value) {
    const firstSelectable = categoryOptions.value.find((x) => x.selectable);
    selectedCategory.value = firstSelectable?.category ?? "";
  }
}

async function startCategoryPractice() {
  loading.value = true;
  error.value = "";
  clearPracticeState();
  try {
    const data = await startPracticeSession(selectedCategory.value || undefined);
    sessionId.value = data.session_id;
    questions.value = data.questions;
  } catch (e) {
    if (axios.isAxiosError(e)) error.value = JSON.stringify(e.response?.data?.detail ?? e.message);
    else error.value = String(e);
  } finally {
    loading.value = false;
  }
}

async function prepareMemorize() {
  if (!selectedCategory.value) {
    error.value = "请先选择分类";
    return;
  }
  loading.value = true;
  error.value = "";
  clearPracticeState();
  memorizePrepared.value = false;
  memorizeIndex.value = 0;
  try {
    const pool = await fetchQuestions({ category: selectedCategory.value });
    if (pool.length < 10) {
      error.value = "该分类不足 10 题，无法进入背题模式";
      memorizeQuestions.value = [];
      return;
    }
    memorizeQuestions.value = shuffle(pool).slice(0, 10);
    memorizePrepared.value = true;
  } catch (e) {
    if (axios.isAxiosError(e)) error.value = JSON.stringify(e.response?.data?.detail ?? e.message);
    else error.value = String(e);
  } finally {
    loading.value = false;
  }
}

function nextMemorize() {
  if (!currentMemorizeQuestion.value) return;
  memorizeIndex.value += 1;
}

async function startQuizFromMemorize() {
  if (memorizeQuestions.value.length !== 10) return;
  loading.value = true;
  error.value = "";
  clearPracticeState();
  try {
    const shuffledIds = shuffle(memorizeQuestions.value.map((q) => q.id));
    const data = await startPracticeSessionCustom(shuffledIds);
    sessionId.value = data.session_id;
    questions.value = data.questions;
    mode.value = "practice";
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
  if (!currentQuestion.value || !sessionId.value) return;
  if (!perQuestionResult[currentQuestion.value.id]) {
    submitting.value = true;
    try {
      const data = await skipPracticeAnswer(sessionId.value, currentQuestion.value.id);
      perQuestionResult[currentQuestion.value.id] = {
        score: data.record.ai_score,
        analysis: data.analysis,
        reference: data.reference_answer
      };
    } catch (e) {
      if (axios.isAxiosError(e)) error.value = JSON.stringify(e.response?.data?.detail ?? e.message);
      else error.value = String(e);
      submitting.value = false;
      return;
    } finally {
      submitting.value = false;
    }
  }
  currentIndex.value += 1;
  answer.value = "";
  error.value = "";
  if (finished.value) {
    summary.value = await fetchPracticeSummary(sessionId.value);
  }
}

onMounted(loadCategories);
</script>

<template>
  <section>
    <h2>训练中心（每次 10 题）</h2>
    <p v-if="error" style="color: #c0392b;">{{ error }}</p>

    <div class="swift-card" style="display: grid; gap: 10px;">
      <div style="display: flex; gap: 8px;">
        <button :disabled="mode === 'practice'" @click="mode = 'practice'">刷题模式</button>
        <button :disabled="mode === 'memorize'" @click="mode = 'memorize'">背题模式</button>
      </div>
      <div style="display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: center;">
        <select v-model="selectedCategory">
          <option value="">全部分类随机</option>
          <option
            v-for="item in categoryOptions"
            :key="item.category"
            :value="item.category"
            :disabled="!item.selectable"
          >
            {{ item.category }}（{{ item.total_questions }}题）{{ item.selectable ? "" : " - 不足10题" }}
          </option>
        </select>
        <button @click="loadCategories">刷新分类</button>
      </div>
    </div>

    <div
      v-if="!questions.length && !loading && mode === 'practice'"
      class="swift-card"
      style="min-height: 44vh; display: grid; place-items: center; margin-top: 12px;"
    >
      <button @click="startCategoryPractice">开始刷题</button>
    </div>

    <div
      v-if="mode === 'memorize' && !memorizePrepared && !loading"
      class="swift-card"
      style="min-height: 44vh; display: grid; place-items: center; margin-top: 12px;"
    >
      <button @click="prepareMemorize">开始背题（10题）</button>
    </div>

    <div v-if="loading" class="swift-card" style="min-height: 200px; display: grid; place-items: center; margin-top: 12px;">
      <LoadingIndicator text="正在准备题目..." />
    </div>

    <div v-if="mode === 'memorize' && memorizePrepared && memorizeIndex < memorizeQuestions.length" class="swift-card" style="margin-top: 12px;">
      <p>背题进度：第 {{ memorizeIndex + 1 }} / 10 题</p>
      <h3>{{ currentMemorizeQuestion?.stem }}</h3>
      <p><strong>参考答案：</strong>{{ currentMemorizeQuestion?.reference_answer || "暂无参考答案" }}</p>
      <button @click="nextMemorize">下一题</button>
    </div>

    <div v-if="mode === 'memorize' && memorizePrepared && memorizeIndex >= 10" class="swift-card" style="margin-top: 12px;">
      <h3>背题完成</h3>
      <p>将进入刷题模式，对刚才这 10 题进行乱序测验。</p>
      <button @click="startQuizFromMemorize">开始测验</button>
    </div>

    <div v-if="currentQuestion && !finished" class="swift-card" style="margin-top: 12px;">
      <p>第 {{ currentIndex + 1 }} / {{ questions.length }} 题</p>
      <h3>{{ currentQuestion.stem }}</h3>
      <p>分类：{{ currentQuestion.category }} | 难度：{{ currentQuestion.difficulty }}</p>

      <textarea v-model="answer" rows="6" style="width: 100%;" placeholder="输入你的答案"></textarea>
      <div style="display: flex; gap: 8px; margin-top: 8px;">
        <button @click="submitCurrent" :disabled="submitting">{{ submitting ? "判题中..." : "提交并判题" }}</button>
        <button @click="nextQuestion">下一题</button>
      </div>
      <LoadingIndicator v-if="submitting" text="AI 正在判题..." />

      <div v-if="perQuestionResult[currentQuestion.id]" style="margin-top: 10px; background: #f7fbff; padding: 10px; border-radius: 10px;">
        <p><strong>得分：</strong>{{ perQuestionResult[currentQuestion.id].score }} / 10</p>
        <p><strong>解析：</strong>{{ perQuestionResult[currentQuestion.id].analysis }}</p>
        <p><strong>参考答案：</strong>{{ perQuestionResult[currentQuestion.id].reference || "-" }}</p>
      </div>
    </div>

    <div v-if="finished && summary" class="swift-card" style="margin-top: 12px;">
      <h3>本轮完成</h3>
      <p><strong>总分：</strong>{{ summary.total_score }} / 100</p>
      <p><strong>记录ID：</strong>{{ summary.record_ids.join(", ") }}</p>
      <p><strong>会话ID：</strong>{{ summary.session_id }}</p>
    </div>
  </section>
</template>
