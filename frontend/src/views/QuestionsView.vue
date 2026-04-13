<script setup lang="ts">
import { Chart, registerables } from "chart.js";
import { computed, nextTick, onMounted, reactive, ref } from "vue";
import LoadingIndicator from "../components/LoadingIndicator.vue";
import {
  fetchQuestionRecords,
  refreshQuestionReferenceAnswer,
  type PracticeRecord,
  type Question
} from "../api/questions";
import { fetchCategories } from "../api/taxonomy";
import { submitDailyPracticeAnswer } from "../api/practice";
import MarkdownRenderer from "../components/MarkdownRenderer.vue";
import { useQuestionStore } from "../stores/questionStore";

Chart.register(...registerables);

const store = useQuestionStore();

const filters = reactive({
  category: "",
  difficulty: "",
  sortMode: "recent_desc"
});
const pager = reactive({
  page: 1,
  pageSize: 20
});
const categoryOptions = ref<string[]>([]);
const filteredMastery = ref(0);

const showActionModal = ref(false);
const selectedQuestion = ref<Question | null>(null);
const editing = ref(false);
const recordsLoaded = ref(false);
const records = ref<PracticeRecord[]>([]);
const singlePracticeAnswer = ref("");
const singlePracticeSubmitting = ref(false);
const singlePracticeResult = ref<{ score: number; analysis: string; reference: string } | null>(null);
const refreshingReference = ref(false);
const scoreChartCanvas = ref<HTMLCanvasElement | null>(null);
let scoreTrendChart: Chart<"line", number[], string> | null = null;

const editForm = reactive({
  stem: "",
  category: "未分类",
  difficulty: 3
});

const sortParams = computed(() => {
  if (filters.sortMode === "created_asc") return { sort_by: "created_at", sort_order: "asc" } as const;
  if (filters.sortMode === "mastery_desc") return { sort_by: "mastery_score", sort_order: "desc" } as const;
  if (filters.sortMode === "mastery_asc") return { sort_by: "mastery_score", sort_order: "asc" } as const;
  if (filters.sortMode === "recent_desc") return { sort_by: "recent_encountered", sort_order: "desc" } as const;
  if (filters.sortMode === "recent_asc") return { sort_by: "recent_encountered", sort_order: "asc" } as const;
  return { sort_by: "created_at", sort_order: "desc" } as const;
});

function recalcMastery() {
  if (!store.items.length) {
    filteredMastery.value = 0;
    return;
  }
  const total = store.items.reduce((sum, q) => sum + (q.mastery_score ?? 0), 0);
  filteredMastery.value = Math.round(total / store.items.length);
}

async function runFilter() {
  await store.loadQuestions({
    category: filters.category.trim() || undefined,
    difficulty: filters.difficulty ? Number(filters.difficulty) : undefined,
    sort_by: sortParams.value.sort_by,
    sort_order: sortParams.value.sort_order,
    page: pager.page,
    page_size: pager.pageSize
  });
  recalcMastery();
}

async function resetFilter() {
  filters.category = "";
  filters.difficulty = "";
  filters.sortMode = "recent_desc";
  pager.page = 1;
  await runFilter();
}

async function changePage(nextPage: number) {
  const totalPages = Math.max(1, Math.ceil((store.total || 0) / pager.pageSize));
  pager.page = Math.max(1, Math.min(totalPages, nextPage));
  await runFilter();
}

function destroyScoreTrendChart() {
  scoreTrendChart?.destroy();
  scoreTrendChart = null;
}

function buildScoreTrendChart() {
  destroyScoreTrendChart();
  const canvas = scoreChartCanvas.value;
  if (!canvas || !records.value.length) return;

  const sorted = [...records.value].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  );
  const labels = sorted.map((r, i) => {
    const t = (r.created_at ?? "").replace("T", " ").slice(0, 16);
    return t || `#${i + 1}`;
  });
  const data = sorted.map((r) => Number(r.ai_score));

  scoreTrendChart = new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "得分 /10",
          data,
          borderColor: "#0969da",
          backgroundColor: "rgba(9, 105, 218, 0.12)",
          fill: true,
          tension: 0.2,
          pointRadius: 3,
          pointHoverRadius: 5
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          min: 0,
          max: 10,
          ticks: { stepSize: 1 }
        }
      },
      plugins: {
        legend: { display: true },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const v = ctx.parsed.y;
              return v != null ? `得分 ${v} / 10` : "";
            }
          }
        }
      }
    }
  });
}

async function openActionModal(q: Question) {
  selectedQuestion.value = q;
  editForm.stem = q.stem;
  editForm.category = q.category;
  editForm.difficulty = q.difficulty;
  editing.value = false;
  showActionModal.value = true;
  recordsLoaded.value = false;
  records.value = [];
  singlePracticeAnswer.value = "";
  singlePracticeResult.value = null;
  destroyScoreTrendChart();
  try {
    records.value = await fetchQuestionRecords(q.id);
  } finally {
    recordsLoaded.value = true;
    await nextTick();
    buildScoreTrendChart();
  }
}

function closeActionModal() {
  destroyScoreTrendChart();
  showActionModal.value = false;
  selectedQuestion.value = null;
  editing.value = false;
  recordsLoaded.value = false;
  singlePracticeAnswer.value = "";
  singlePracticeResult.value = null;
}

async function saveEdit() {
  if (!selectedQuestion.value) return;
  if (editForm.stem.trim().length < 3) return;
  await store.editQuestion(selectedQuestion.value.id, {
    stem: editForm.stem.trim(),
    category: editForm.category.trim() || "未分类",
    difficulty: Number(editForm.difficulty)
  });
  editing.value = false;
  await runFilter();
}

async function removeCurrent() {
  if (!selectedQuestion.value) return;
  const yes = window.confirm("确认删除这道题吗？");
  if (!yes) return;
  await store.removeQuestion(selectedQuestion.value.id);
  closeActionModal();
  await runFilter();
}

async function loadRecords() {
  if (!selectedQuestion.value) return;
  records.value = await fetchQuestionRecords(selectedQuestion.value.id);
  recordsLoaded.value = true;
  await nextTick();
  buildScoreTrendChart();
}

async function refreshSelectedReference() {
  if (!selectedQuestion.value) return;
  refreshingReference.value = true;
  try {
    const latest = await refreshQuestionReferenceAnswer(selectedQuestion.value.id);
    selectedQuestion.value = latest;
    editForm.stem = latest.stem;
    editForm.category = latest.category;
    editForm.difficulty = latest.difficulty;
    await runFilter();
  } finally {
    refreshingReference.value = false;
  }
}

async function submitSingleQuestionPractice() {
  if (!selectedQuestion.value) return;
  if (!singlePracticeAnswer.value.trim()) return;
  singlePracticeSubmitting.value = true;
  try {
    const data = await submitDailyPracticeAnswer(selectedQuestion.value.id, singlePracticeAnswer.value.trim());
    singlePracticeResult.value = {
      score: data.record.ai_score,
      analysis: data.analysis,
      reference: data.reference_answer
    };
    await loadRecords();
  } finally {
    singlePracticeSubmitting.value = false;
  }
}

function difficultyStars(level: number): string {
  const n = Math.max(1, Math.min(5, Number(level || 1)));
  return "★".repeat(n) + "☆".repeat(5 - n);
}

function progressStyle(mastery: number) {
  const pct = Math.max(0, Math.min(100, Number(mastery || 0)));
  const edge = Math.min(100, pct + 12);
  return {
    background: `linear-gradient(90deg, rgba(209,235,214,0.85) 0%, rgba(209,235,214,0.65) ${pct}%, #ffffff ${edge}%, #ffffff 100%)`
  };
}

onMounted(async () => {
  const cats = await fetchCategories();
  categoryOptions.value = cats.map((c) => c.name);
  await runFilter();
});
</script>

<template>
  <section>
    <h2>题库管理</h2>
    <p>
      当前页题数：{{ store.items.length }} / 总题数：{{ store.total }}，当前页平均掌握程度：{{ filteredMastery }}%
    </p>

    <div class="swift-card" style="display: grid; gap: 10px; margin-bottom: 14px;">
      <h3 style="margin: 0;">筛选</h3>
      <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px;">
        <select v-model="filters.category" @change="changePage(1)">
          <option value="">全部分类</option>
          <option v-for="c in categoryOptions" :key="c" :value="c">{{ c }}</option>
        </select>
        <select v-model="filters.difficulty" @change="changePage(1)">
          <option value="">全部难度</option>
          <option value="1">难度 1</option>
          <option value="2">难度 2</option>
          <option value="3">难度 3</option>
          <option value="4">难度 4</option>
          <option value="5">难度 5</option>
        </select>
        <select v-model="filters.sortMode" @change="changePage(1)">
          <option value="recent_desc">最近遇到：近到远（默认）</option>
          <option value="recent_asc">最近遇到：远到近</option>
          <option value="created_desc">入库时间：新到旧</option>
          <option value="created_asc">入库时间：旧到新</option>
          <option value="mastery_desc">掌握度：高到低</option>
          <option value="mastery_asc">掌握度：低到高</option>
        </select>
      </div>
      <div style="display: flex; gap: 8px;">
        <button @click="runFilter">刷新</button>
        <button @click="resetFilter">重置</button>
        <select v-model.number="pager.pageSize" @change="changePage(1)">
          <option :value="10">每页 10</option>
          <option :value="20">每页 20</option>
          <option :value="50">每页 50</option>
          <option :value="100">每页 100</option>
        </select>
      </div>
    </div>

    <p v-if="store.loading">加载中...</p>
    <div v-else style="display: grid; gap: 10px;">
      <div
        v-for="q in store.items"
        :key="q.id"
        :style="progressStyle(q.mastery_score)"
        class="swift-card"
        style="padding: 12px;"
      >
        <div style="font-size: 16px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.3px;">
          {{ q.stem }}
        </div>
        <div style="font-size: 13px; color: #465162; margin-top: 6px;">
          分类：{{ q.category }} ｜ 难度：{{ difficultyStars(q.difficulty) }} ｜ 完成度：{{ q.mastery_score }}%
        </div>
        <div style="font-size: 12px; color: #667085; margin-top: 4px;">
          入库时间：{{ q.created_at }}
        </div>
        <div style="margin-top: 8px;">
          <button @click="openActionModal(q)">查看与操作</button>
        </div>
      </div>
    </div>

    <div style="display: flex; gap: 8px; align-items: center; margin-top: 12px;">
      <button @click="changePage(pager.page - 1)" :disabled="pager.page <= 1">上一页</button>
      <span>第 {{ pager.page }} / {{ Math.max(1, Math.ceil((store.total || 0) / pager.pageSize)) }} 页</span>
      <button
        @click="changePage(pager.page + 1)"
        :disabled="pager.page >= Math.max(1, Math.ceil((store.total || 0) / pager.pageSize))"
      >
        下一页
      </button>
    </div>

    <teleport to="body">
      <div
        v-if="showActionModal && selectedQuestion"
        style="position: fixed; inset: 0; z-index: 1200; background: rgba(17,24,39,0.36); display: grid; place-items: center;"
      >
        <div class="swift-card q-modal-panel">
          <button @click="closeActionModal" class="q-modal-close-btn">关闭</button>
          <h3 style="margin-top: 0;">题目详情与操作</h3>
          <p><strong>题目：</strong>{{ selectedQuestion.stem }}</p>
          <div>
            <strong>参考答案：</strong>
            <MarkdownRenderer v-if="selectedQuestion.reference_answer?.trim()" :source="selectedQuestion.reference_answer" />
            <span v-else>暂无</span>
          </div>

          <div style="display: flex; gap: 8px; margin: 10px 0;">
            <button @click="editing = true">编辑题目</button>
            <button @click="removeCurrent">删除题目</button>
            <button @click="loadRecords">刷新做题记录</button>
            <button @click="refreshSelectedReference" :disabled="refreshingReference">
              {{ refreshingReference ? "刷新中..." : "仅刷新参考答案" }}
            </button>
          </div>

          <div style="margin-top: 12px; border: 1px solid #e6eaf2; padding: 10px; border-radius: 12px;">
            <h4 style="margin: 0 0 8px;">单独做这道题（独立判题）</h4>
            <textarea v-model="singlePracticeAnswer" rows="5" style="width: 100%;" placeholder="输入你的答案"></textarea>
            <div style="display: flex; gap: 8px; margin-top: 8px;">
              <button @click="submitSingleQuestionPractice" :disabled="singlePracticeSubmitting || !singlePracticeAnswer.trim()">
                {{ singlePracticeSubmitting ? "判题中..." : "提交并判题" }}
              </button>
            </div>
            <LoadingIndicator v-if="singlePracticeSubmitting" text="AI 正在判题..." />
            <div v-if="singlePracticeResult" style="margin-top: 10px; background: #f7fbff; padding: 10px; border-radius: 10px;">
              <p><strong>得分：</strong>{{ singlePracticeResult.score }} / 10</p>
              <div>
                <strong>解析：</strong>
                <MarkdownRenderer v-if="singlePracticeResult.analysis?.trim()" :source="singlePracticeResult.analysis" />
                <span v-else>-</span>
              </div>
              <div>
                <strong>参考答案：</strong>
                <MarkdownRenderer v-if="singlePracticeResult.reference?.trim()" :source="singlePracticeResult.reference" />
                <span v-else>-</span>
              </div>
            </div>
          </div>

          <div v-if="editing" style="display: grid; gap: 8px; border: 1px solid #e6eaf2; padding: 10px; border-radius: 12px;">
            <textarea v-model="editForm.stem" rows="3"></textarea>
            <input v-model="editForm.category" />
            <input v-model.number="editForm.difficulty" type="number" min="1" max="5" />
            <div style="display: flex; gap: 8px;">
              <button @click="saveEdit">保存</button>
              <button @click="editing = false">取消</button>
            </div>
          </div>

          <div v-if="recordsLoaded" style="margin-top: 12px;">
            <h4 style="margin-bottom: 6px;">每次得分趋势</h4>
            <p v-if="records.length === 0" style="color: #57606a; font-size: 13px; margin: 0 0 10px;">
              暂无做题记录，无折线图。
            </p>
            <div v-else class="q-score-chart-wrap">
              <canvas ref="scoreChartCanvas" />
            </div>
            <template v-if="records.length">
              <h4 style="margin: 16px 0 6px;">做题记录</h4>
              <div style="display: grid; gap: 8px;">
                <div v-for="r in records" :key="r.id" style="border: 1px solid #dde3ee; padding: 8px; border-radius: 10px;">
                  <div><strong>评分：</strong>{{ r.ai_score }}/10</div>
                  <div><strong>用户答案：</strong>{{ r.user_answer || "-" }}</div>
                  <div>
                    <strong>AI 解析：</strong>
                    <MarkdownRenderer v-if="r.ai_answer?.trim()" :source="r.ai_answer" />
                    <span v-else>-</span>
                  </div>
                  <div style="font-size: 12px; color: #666;">时间：{{ r.created_at }}</div>
                </div>
              </div>
            </template>
          </div>

        </div>
      </div>
    </teleport>
  </section>
</template>

<style scoped>
.q-modal-panel {
  position: relative;
  width: 920px;
  max-width: 95vw;
  max-height: 88vh;
  overflow: auto;
  padding: 16px;
}

.q-modal-close-btn {
  position: sticky;
  top: 8px;
  margin-left: auto;
  display: block;
  z-index: 10;
}

.q-score-chart-wrap {
  position: relative;
  height: 220px;
  max-width: 100%;
}
</style>
