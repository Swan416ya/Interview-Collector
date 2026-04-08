<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import LoadingIndicator from "../components/LoadingIndicator.vue";
import { fetchPracticeSessions, submitDailyPracticeAnswer } from "../api/practice";
import { fetchQuestions, type Question } from "../api/questions";
import { mockUserProfile } from "../mock/userProfile";

interface HeatCell {
  date: string;
  count: number;
  level: number;
}

const loading = ref(false);
const heatCells = ref<HeatCell[]>([]);
const totalSessions = ref(0);
const totalDaysActive = ref(0);
const dailyQuestion = ref<Question | null>(null);
const dailyQuestionIndex = ref(0);
const showDailyModal = ref(false);
const dailyAnswer = ref("");
const dailySubmitting = ref(false);
const dailyResult = ref<{ score: number; analysis: string; reference: string } | null>(null);

function toDateKey(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function levelByCount(count: number): number {
  if (count <= 0) return 0;
  if (count === 1) return 1;
  if (count <= 2) return 2;
  if (count <= 4) return 3;
  return 4;
}

const levelColor = (level: number) => {
  if (level === 0) return "#ebedf0";
  if (level === 1) return "#c6e48b";
  if (level === 2) return "#7bc96f";
  if (level === 3) return "#239a3b";
  return "#196127";
};

const weeklyRows = computed(() => {
  const rows: HeatCell[][] = [];
  for (let i = 0; i < heatCells.value.length; i += 7) rows.push(heatCells.value.slice(i, i + 7));
  return rows;
});

async function loadHomeData() {
  loading.value = true;
  try {
    const [sessions, questions] = await Promise.all([
      fetchPracticeSessions(),
      fetchQuestions({ sort_by: "mastery_score", sort_order: "asc" })
    ]);

    const counts = new Map<string, number>();
    for (const s of sessions) {
      const dateStr = s.completed_at || s.created_at;
      const key = dateStr.slice(0, 10);
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }

    const today = new Date();
    const days = 140;
    const cells: HeatCell[] = [];
    for (let i = days - 1; i >= 0; i--) {
      const d = new Date(today);
      d.setDate(today.getDate() - i);
      const key = toDateKey(d);
      const count = counts.get(key) ?? 0;
      cells.push({ date: key, count, level: levelByCount(count) });
    }
    heatCells.value = cells;
    totalSessions.value = sessions.length;
    totalDaysActive.value = cells.filter((c) => c.count > 0).length;

    if (questions.length) {
      const idx = new Date().getDate() % questions.length;
      dailyQuestionIndex.value = idx;
      dailyQuestion.value = questions[idx];
    } else {
      dailyQuestion.value = null;
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

    <div style="margin-top: 16px; border: 1px solid #ddd; border-radius: 8px; padding: 12px;">
      <h3 style="margin-top: 0;">刷题活跃图</h3>
      <p style="color: #666;">
        最近 140 天刷题轮次：{{ totalSessions }} 次，活跃天数：{{ totalDaysActive }} 天
      </p>
      <p v-if="loading">加载中...</p>
      <div v-else style="display: flex; gap: 3px; flex-wrap: nowrap; overflow-x: auto;">
        <div v-for="(week, idx) in weeklyRows" :key="idx" style="display: grid; gap: 3px;">
          <div
            v-for="cell in week"
            :key="cell.date"
            :title="`${cell.date} 刷题 ${cell.count} 次`"
            :style="{
              width: '12px',
              height: '12px',
              borderRadius: '2px',
              background: levelColor(cell.level)
            }"
          />
        </div>
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
            <p><strong>解析：</strong>{{ dailyResult.analysis }}</p>
            <p><strong>参考答案：</strong>{{ dailyResult.reference || "-" }}</p>
          </div>
        </div>
      </div>
    </teleport>
  </section>
</template>

