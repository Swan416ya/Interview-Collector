<script setup lang="ts">
import axios from "axios";
import { computed, onMounted, reactive, ref, watch } from "vue";
import LoadingIndicator from "../components/LoadingIndicator.vue";
import MarkdownRenderer from "../components/MarkdownRenderer.vue";
import { fetchQuestions, type Question } from "../api/questions";
import {
  fetchPracticeCategories,
  fetchPracticeSummary,
  skipPracticeAnswer,
  startPracticeSession,
  startPracticeSessionCustom,
  submitPracticeAnswer,
  type PracticeCategoryOption,
  type PracticeSessionSize,
  type PracticeSummaryResponse
} from "../api/practice";

type TrainMode = "practice" | "memorize";

const mode = ref<TrainMode>("practice");
const categoryOptions = ref<PracticeCategoryOption[]>([]);
const totalQuestionsAll = ref(0);
const selectedCategory = ref("");
const sessionSize = ref<PracticeSessionSize>(10);
const SESSION_SIZES: PracticeSessionSize[] = [5, 10, 15];

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

const canStartPractice = computed(() => {
  const n = sessionSize.value;
  if (!selectedCategory.value) return totalQuestionsAll.value >= n;
  const opt = categoryOptions.value.find((c) => c.category === selectedCategory.value);
  return (opt?.total_questions ?? 0) >= n;
});

/** 背题必须选具体分类，且该分类题量不少于本轮题量 */
const canStartMemorize = computed(() => {
  if (!selectedCategory.value) return false;
  const opt = categoryOptions.value.find((c) => c.category === selectedCategory.value);
  return (opt?.total_questions ?? 0) >= sessionSize.value;
});

const summaryMaxScore = computed(() => {
  const qc = summary.value?.question_count;
  if (qc != null && qc > 0) return qc * 10;
  const len = questions.value.length;
  return len > 0 ? len * 10 : 100;
});

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
  const data = await fetchPracticeCategories();
  categoryOptions.value = data.categories;
  totalQuestionsAll.value = data.total_questions_all;
  if (!selectedCategory.value) {
    const firstOk = data.categories.find((x) => x.total_questions >= sessionSize.value);
    selectedCategory.value = firstOk?.category ?? "";
  }
}

async function startCategoryPractice() {
  if (!canStartPractice.value) {
    error.value = selectedCategory.value
      ? `该分类题目不足 ${sessionSize.value} 道，请换分类或减小题量`
      : `全库题目不足 ${sessionSize.value} 道，请减小题量或先导入题目`;
    return;
  }
  loading.value = true;
  error.value = "";
  clearPracticeState();
  try {
    const data = await startPracticeSession(selectedCategory.value || undefined, sessionSize.value);
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
  if (!canStartMemorize.value) {
    error.value = `该分类题目不足 ${sessionSize.value} 道，请换分类或减小题量`;
    return;
  }
  const n = sessionSize.value;
  loading.value = true;
  error.value = "";
  clearPracticeState();
  memorizePrepared.value = false;
  memorizeIndex.value = 0;
  try {
    const pool = await fetchQuestions({ category: selectedCategory.value });
    if (pool.length < n) {
      error.value = `该分类不足 ${n} 题，无法进入背题模式`;
      memorizeQuestions.value = [];
      return;
    }
    memorizeQuestions.value = shuffle(pool).slice(0, n);
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
  const n = sessionSize.value;
  if (memorizeQuestions.value.length !== n) return;
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

watch(sessionSize, () => {
  memorizePrepared.value = false;
  memorizeQuestions.value = [];
  memorizeIndex.value = 0;
  if (!selectedCategory.value) return;
  const opt = categoryOptions.value.find((c) => c.category === selectedCategory.value);
  if (opt && opt.total_questions < sessionSize.value) {
    const next = categoryOptions.value.find((c) => c.total_questions >= sessionSize.value);
    selectedCategory.value = next?.category ?? "";
  }
});

watch(mode, (m) => {
  if (m !== "memorize") return;
  memorizePrepared.value = false;
  memorizeQuestions.value = [];
  memorizeIndex.value = 0;
  if (selectedCategory.value) return;
  const ok = categoryOptions.value.find((c) => c.total_questions >= sessionSize.value);
  selectedCategory.value = ok?.category ?? "";
});

onMounted(loadCategories);
</script>

<template>
  <section>
    <h2>训练中心</h2>
    <p v-if="error" style="color: #c0392b;">{{ error }}</p>

    <div class="swift-card" style="display: grid; gap: 10px;">
      <div style="display: flex; gap: 8px;">
        <button :disabled="mode === 'practice'" @click="mode = 'practice'">刷题模式</button>
        <button :disabled="mode === 'memorize'" @click="mode = 'memorize'">背题模式</button>
      </div>
      <div style="display: flex; flex-wrap: wrap; gap: 12px; align-items: center;">
        <span style="font-size: 14px; color: #444;">本轮题量：</span>
        <label v-for="n in SESSION_SIZES" :key="n" style="display: inline-flex; gap: 4px; align-items: center; cursor: pointer;">
          <input v-model.number="sessionSize" type="radio" name="sessionSize" :value="n" />
          {{ n }} 题
        </label>
      </div>
      <div style="display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: center;">
        <select v-model="selectedCategory">
          <option v-if="mode === 'practice'" value="">全部分类随机</option>
          <option
            v-for="item in categoryOptions"
            :key="item.category"
            :value="item.category"
            :disabled="item.total_questions < sessionSize"
          >
            {{ item.category }}（{{ item.total_questions }}题）{{
              item.total_questions < sessionSize ? ` — 不足${sessionSize}题` : ""
            }}
          </option>
        </select>
        <button @click="loadCategories">刷新分类</button>
      </div>
      <p v-if="mode === 'practice'" style="margin: 0; font-size: 13px; color: #667085;">
        全库共 {{ totalQuestionsAll }} 题；选「全部分类」时需全库 ≥ 所选题量，选具体分类时需该分类 ≥ 所选题量。
      </p>
      <p v-if="mode === 'memorize'" style="margin: 0; font-size: 13px; color: #667085;">
        背题需选择<strong>具体分类</strong>（不能用「全部分类」），且该分类题量 ≥ {{ sessionSize }}。
      </p>
    </div>

    <div
      v-if="!questions.length && !loading && mode === 'practice'"
      class="swift-card"
      style="min-height: 44vh; display: grid; place-items: center; margin-top: 12px;"
    >
      <button @click="startCategoryPractice" :disabled="!canStartPractice">开始刷题（{{ sessionSize }} 题）</button>
    </div>

    <div
      v-if="mode === 'memorize' && !memorizePrepared && !loading"
      class="swift-card"
      style="min-height: 44vh; display: grid; place-items: center; margin-top: 12px;"
    >
      <button @click="prepareMemorize" :disabled="!canStartMemorize">
        开始背题（{{ sessionSize }} 题）
      </button>
    </div>

    <div v-if="loading" class="swift-card" style="min-height: 200px; display: grid; place-items: center; margin-top: 12px;">
      <LoadingIndicator text="正在准备题目..." />
    </div>

    <div v-if="mode === 'memorize' && memorizePrepared && memorizeIndex < memorizeQuestions.length" class="swift-card" style="margin-top: 12px;">
      <p>背题进度：第 {{ memorizeIndex + 1 }} / {{ memorizeQuestions.length }} 题</p>
      <h3>{{ currentMemorizeQuestion?.stem }}</h3>
      <div>
        <strong>参考答案：</strong>
        <MarkdownRenderer
          v-if="currentMemorizeQuestion?.reference_answer?.trim()"
          :source="currentMemorizeQuestion.reference_answer"
        />
        <span v-else>暂无参考答案</span>
      </div>
      <button @click="nextMemorize">下一题</button>
    </div>

    <div
      v-if="mode === 'memorize' && memorizePrepared && memorizeIndex >= memorizeQuestions.length && memorizeQuestions.length > 0"
      class="swift-card"
      style="margin-top: 12px;"
    >
      <h3>背题完成</h3>
      <p>将进入刷题模式，对刚才这 {{ memorizeQuestions.length }} 题进行乱序测验。</p>
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
      <LoadingIndicator
        v-if="submitting"
        text="AI 正在判题（云端约 10–30 秒，请稍候；勿重复点击）"
      />

      <div v-if="perQuestionResult[currentQuestion.id]" style="margin-top: 10px; background: #f7fbff; padding: 10px; border-radius: 10px;">
        <p><strong>得分：</strong>{{ perQuestionResult[currentQuestion.id].score }} / 10</p>
        <div>
          <strong>解析：</strong>
          <MarkdownRenderer
            v-if="perQuestionResult[currentQuestion.id].analysis?.trim()"
            :source="perQuestionResult[currentQuestion.id].analysis"
          />
          <span v-else>-</span>
        </div>
        <div>
          <strong>参考答案：</strong>
          <MarkdownRenderer
            v-if="perQuestionResult[currentQuestion.id].reference?.trim()"
            :source="perQuestionResult[currentQuestion.id].reference"
          />
          <span v-else>-</span>
        </div>
      </div>
    </div>

    <div v-if="finished && summary" class="swift-card" style="margin-top: 12px;">
      <h3>本轮完成</h3>
      <p><strong>总分：</strong>{{ summary.total_score }} / {{ summaryMaxScore }}</p>
      <p><strong>记录ID：</strong>{{ summary.record_ids.join(", ") }}</p>
      <p><strong>会话ID：</strong>{{ summary.session_id }}</p>
    </div>
  </section>
</template>
