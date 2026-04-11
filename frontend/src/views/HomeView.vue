<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import LoadingIndicator from "../components/LoadingIndicator.vue";
import MarkdownRenderer from "../components/MarkdownRenderer.vue";
import { fetchPracticeActivity, submitDailyPracticeAnswer } from "../api/practice";
import type { PracticeActivityDay, PracticeActivityResponse } from "../api/practice";
import { fetchQuestionRecords, fetchQuestions, type Question } from "../api/questions";
import { mockUserProfile } from "../mock/userProfile";

const loading = ref(false);
const activity = ref<PracticeActivityResponse | null>(null);
const dailyQuestion = ref<Question | null>(null);
const dailyQuestionIndex = ref(0);
const showDailyModal = ref(false);
const dailyAnswer = ref("");
const dailySubmitting = ref(false);
const dailyResult = ref<{ score: number; analysis: string; reference: string } | null>(null);
const dailyDoneScore = ref<number | null>(null);

function toDateKey(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/** Colors aligned with GitHub contribution graph tiers (0–4 from API). */
function levelColor(level: number): string {
  if (level <= 0) return "#ebedf0";
  if (level === 1) return "#9be9a8";
  if (level === 2) return "#40c463";
  if (level === 3) return "#30a14e";
  return "#216e39";
}

const weekColumns = computed((): PracticeActivityDay[][] => {
  const days = activity.value?.days ?? [];
  const cols: PracticeActivityDay[][] = [];
  const nWeeks = Math.max(1, Math.ceil(days.length / 7));
  for (let w = 0; w < nWeeks; w++) {
    cols.push(days.slice(w * 7, w * 7 + 7));
  }
  return cols;
});

const monthLabels = computed(() => {
  const cols = weekColumns.value;
  const names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  let prevKey = "";
  return cols.map((col) => {
    const top = col[0]?.date;
    if (!top) return "";
    const key = top.slice(0, 7);
    if (key === prevKey) return "";
    prevKey = key;
    const m = Number(top.slice(5, 7)) - 1;
    return names[m] ?? "";
  });
});

function cellTitle(cell: { date: string; count: number }, today: string): string {
  if (cell.date > today) return `${cell.date}（未到）`;
  if (cell.count <= 0) return `${cell.date} 0 道题`;
  return `${cell.date} ${cell.count} 道题`;
}

async function loadHomeData() {
  loading.value = true;
  try {
    const [act, questions] = await Promise.all([
      fetchPracticeActivity(),
      fetchQuestions({ sort_by: "mastery_score", sort_order: "asc" })
    ]);
    activity.value = act;

    if (questions.length) {
      const idx = new Date().getDate() % questions.length;
      dailyQuestionIndex.value = idx;
      dailyQuestion.value = questions[idx];
      const records = await fetchQuestionRecords(questions[idx].id);
      const todayKey = toDateKey(new Date());
      const todayRecord = records.find((r) => (r.created_at ?? "").slice(0, 10) === todayKey);
      dailyDoneScore.value = todayRecord ? Number(todayRecord.ai_score) : null;
    } else {
      dailyQuestion.value = null;
      dailyDoneScore.value = null;
    }
  } finally {
    loading.value = false;
  }
}

onMounted(loadHomeData);

function openDailyModal() {
  if (!dailyQuestion.value) return;
  showDailyModal.value = true;
  dailyAnswer.value = "";
  dailyResult.value = null;
}

async function submitDailyAnswer() {
  if (!dailyQuestion.value) return;
  if (!dailyAnswer.value.trim()) return;
  dailySubmitting.value = true;
  try {
    const data = await submitDailyPracticeAnswer(dailyQuestion.value.id, dailyAnswer.value.trim());
    dailyResult.value = {
      score: data.record.ai_score,
      analysis: data.analysis,
      reference: data.reference_answer
    };
    dailyDoneScore.value = data.record.ai_score;
    await loadHomeData();
  } finally {
    dailySubmitting.value = false;
  }
}
</script>

<template>
  <section>
    <h2>用户主页</h2>
    <div style="display: flex; gap: 14px; align-items: center; border: 1px solid #ddd; border-radius: 8px; padding: 12px;">
      <img :src="mockUserProfile.avatarUrl" alt="avatar" width="72" height="72" style="border-radius: 50%;" />
      <div>
        <div style="font-size: 20px; font-weight: 700;">{{ mockUserProfile.username }}</div>
        <div style="color: #666;">UID: {{ mockUserProfile.uid }}</div>
        <div style="margin-top: 4px;">{{ mockUserProfile.bio }}</div>
      </div>
    </div>

    <div class="gh-card">
      <h3 class="gh-card-title">做题热力图</h3>
      <p class="gh-card-desc">
        按 <strong>Asia/Shanghai</strong> 日历日统计 <code>practice_records</code>（每次提交 / 跳过 / 每日一题各记 1 题）。最近 53 周 · 窗口内共
        <strong>{{ activity?.total_questions ?? "—" }}</strong>
        题，活跃
        <strong>{{ activity?.active_days ?? "—" }}</strong>
        天。
      </p>
      <p v-if="loading" class="gh-muted">加载中...</p>
      <div v-else-if="activity" class="gh-graph-wrap">
        <div class="gh-graph-main">
          <div class="gh-dow-col" aria-hidden="true">
            <div class="gh-dow-spacer" />
            <span class="gh-dow-slot gh-dow-empty" />
            <span class="gh-dow-slot gh-dow">Mon</span>
            <span class="gh-dow-slot gh-dow-empty" />
            <span class="gh-dow-slot gh-dow">Wed</span>
            <span class="gh-dow-slot gh-dow-empty" />
            <span class="gh-dow-slot gh-dow">Fri</span>
            <span class="gh-dow-slot gh-dow-empty" />
          </div>
          <div class="gh-grid-area">
            <div class="gh-months-row">
              <span v-for="(lab, idx) in monthLabels" :key="idx" class="gh-month">{{ lab }}</span>
            </div>
            <div class="gh-weeks-row">
              <div v-for="(col, ci) in weekColumns" :key="ci" class="gh-week-col">
                <div
                  v-for="(cell, ri) in col"
                  :key="ri"
                  class="gh-cell"
                  :style="{ background: levelColor(cell.level) }"
                  :title="cellTitle(cell, activity.today)"
                />
              </div>
            </div>
          </div>
        </div>
        <div class="gh-legend">
          <span class="gh-legend-less">Less</span>
          <span class="gh-legend-swatch" style="background: #ebedf0" />
          <span class="gh-legend-swatch" style="background: #9be9a8" />
          <span class="gh-legend-swatch" style="background: #40c463" />
          <span class="gh-legend-swatch" style="background: #30a14e" />
          <span class="gh-legend-swatch" style="background: #216e39" />
          <span class="gh-legend-more">More</span>
        </div>
        <p class="gh-footnote">
          色阶：0 题灰 · 1–9 浅绿 · 10–19 中绿 · 20–49 深绿 · 50 题及以上最深绿。
        </p>
      </div>
    </div>

    <div style="margin-top: 16px; border: 1px solid #ddd; border-radius: 8px; padding: 12px;">
      <h3 style="margin-top: 0;">每日一题</h3>
      <div v-if="dailyQuestion">
        <div style="font-size: 13px; color: #666;">今日推荐索引：#{{ dailyQuestionIndex + 1 }}</div>
        <div style="margin-top: 6px;"><strong>{{ dailyQuestion.stem }}</strong></div>
        <div style="margin-top: 6px; color: #444;">
          分类：{{ dailyQuestion.category }} ｜ 难度：{{ dailyQuestion.difficulty }} ｜ 当前掌握：{{ dailyQuestion.mastery_score }}%
        </div>
        <div v-if="dailyDoneScore !== null" style="margin-top: 8px; color: #1e7f3b; font-weight: 600;">
          今日已完成（{{ dailyDoneScore }}/10）
        </div>
        <div style="margin-top: 10px;">
          <button @click="openDailyModal">做题</button>
        </div>
      </div>
      <p v-else>暂无题目，请先导入或新增题目。</p>
    </div>

    <teleport to="body">
      <div
        v-if="showDailyModal && dailyQuestion"
        style="position: fixed; inset: 0; z-index: 1200; background: rgba(17,24,39,0.36); display: grid; place-items: center;"
      >
        <div class="swift-card" style="width: 900px; max-width: 95vw; max-height: 88vh; overflow: auto; padding: 16px;">
          <h3 style="margin-top: 0;">每日一题作答</h3>
          <p><strong>题目：</strong>{{ dailyQuestion.stem }}</p>
          <textarea v-model="dailyAnswer" rows="7" style="width: 100%;" placeholder="输入你的答案"></textarea>
          <div style="display: flex; gap: 8px; margin-top: 8px;">
            <button @click="submitDailyAnswer" :disabled="dailySubmitting">
              {{ dailySubmitting ? "判题中..." : "提交并判题" }}
            </button>
            <button @click="showDailyModal = false">关闭</button>
          </div>
          <LoadingIndicator v-if="dailySubmitting" text="AI 正在判题..." />
          <div v-if="dailyResult" style="margin-top: 10px; background: #f7fbff; padding: 10px; border-radius: 10px;">
            <p><strong>得分：</strong>{{ dailyResult.score }} / 10</p>
            <div>
              <strong>解析：</strong>
              <MarkdownRenderer v-if="dailyResult.analysis?.trim()" :source="dailyResult.analysis" />
              <span v-else>-</span>
            </div>
            <div>
              <strong>参考答案：</strong>
              <MarkdownRenderer v-if="dailyResult.reference?.trim()" :source="dailyResult.reference" />
              <span v-else>-</span>
            </div>
          </div>
        </div>
      </div>
    </teleport>
  </section>
</template>

<style scoped>
.gh-card {
  margin-top: 16px;
  border: 1px solid #d0d7de;
  border-radius: 8px;
  padding: 14px 16px 12px;
  background: #fff;
}

.gh-card-title {
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 600;
}

.gh-card-desc {
  margin: 0 0 12px;
  font-size: 13px;
  color: #57606a;
  line-height: 1.5;
}

.gh-card-desc code {
  font-size: 12px;
  padding: 1px 5px;
  border-radius: 4px;
  background: #f6f8fa;
}

.gh-muted {
  color: #57606a;
  font-size: 13px;
}

.gh-graph-wrap {
  overflow-x: auto;
  padding-bottom: 4px;
}

.gh-graph-main {
  display: flex;
  gap: 4px;
  align-items: flex-end;
  min-width: min-content;
}

.gh-dow-col {
  display: flex;
  flex-direction: column;
  width: 28px;
  flex-shrink: 0;
  padding-bottom: 0;
}

.gh-dow-spacer {
  height: 14px;
  flex-shrink: 0;
}

.gh-dow-slot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  height: 10px;
  margin-bottom: 3px;
  font-size: 9px;
  line-height: 1;
  color: #57606a;
  padding-right: 2px;
  box-sizing: border-box;
}

.gh-dow-slot:last-child {
  margin-bottom: 0;
}

.gh-dow-empty {
  visibility: hidden;
}

.gh-grid-area {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.gh-months-row {
  display: flex;
  flex-direction: row;
  gap: 3px;
  height: 14px;
  align-items: flex-end;
}

.gh-month {
  width: 10px;
  flex: 0 0 10px;
  font-size: 9px;
  line-height: 1;
  color: #57606a;
  white-space: nowrap;
  overflow: visible;
  position: relative;
  z-index: 1;
}

.gh-weeks-row {
  display: flex;
  flex-direction: row;
  gap: 3px;
}

.gh-week-col {
  display: flex;
  flex-direction: column;
  gap: 3px;
  width: 10px;
  flex: 0 0 10px;
}

.gh-cell {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  outline: 1px solid rgba(27, 31, 36, 0.06);
  outline-offset: -1px;
  flex-shrink: 0;
}

.gh-legend {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: flex-end;
  gap: 3px;
  margin-top: 10px;
  font-size: 10px;
  color: #57606a;
}

.gh-legend-less {
  margin-right: 4px;
}

.gh-legend-more {
  margin-left: 4px;
}

.gh-legend-swatch {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  outline: 1px solid rgba(27, 31, 36, 0.06);
  outline-offset: -1px;
}

.gh-footnote {
  margin: 8px 0 0;
  font-size: 11px;
  color: #6e7781;
  text-align: right;
}
</style>
