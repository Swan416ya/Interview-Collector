<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { fetchQuestionRecords, type PracticeRecord, type Question } from "../api/questions";
import { fetchCategories } from "../api/taxonomy";
import { useQuestionStore } from "../stores/questionStore";

const store = useQuestionStore();

const filters = reactive({
  category: "",
  difficulty: "",
  sortMode: "created_desc"
});
const categoryOptions = ref<string[]>([]);
const filteredMastery = ref(0);

const showActionModal = ref(false);
const selectedQuestion = ref<Question | null>(null);
const editing = ref(false);
const recordsLoaded = ref(false);
const records = ref<PracticeRecord[]>([]);

const editForm = reactive({
  stem: "",
  category: "未分类",
  difficulty: 3
});

const sortParams = computed(() => {
  if (filters.sortMode === "created_asc") return { sort_by: "created_at", sort_order: "asc" } as const;
  if (filters.sortMode === "mastery_desc") return { sort_by: "mastery_score", sort_order: "desc" } as const;
  if (filters.sortMode === "mastery_asc") return { sort_by: "mastery_score", sort_order: "asc" } as const;
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
    sort_order: sortParams.value.sort_order
  });
  recalcMastery();
}

async function resetFilter() {
  filters.category = "";
  filters.difficulty = "";
  filters.sortMode = "created_desc";
  await runFilter();
}

function openActionModal(q: Question) {
  selectedQuestion.value = q;
  editForm.stem = q.stem;
  editForm.category = q.category;
  editForm.difficulty = q.difficulty;
  editing.value = false;
  recordsLoaded.value = false;
  records.value = [];
  showActionModal.value = true;
}

function closeActionModal() {
  showActionModal.value = false;
  selectedQuestion.value = null;
  editing.value = false;
  recordsLoaded.value = false;
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
    <p>当前筛选结果题数：{{ store.items.length }}，总掌握程度：{{ filteredMastery }}%</p>

    <div class="swift-card" style="display: grid; gap: 10px; margin-bottom: 14px;">
      <h3 style="margin: 0;">筛选</h3>
      <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px;">
        <select v-model="filters.category" @change="runFilter">
          <option value="">全部分类</option>
          <option v-for="c in categoryOptions" :key="c" :value="c">{{ c }}</option>
        </select>
        <select v-model="filters.difficulty" @change="runFilter">
          <option value="">全部难度</option>
          <option value="1">难度 1</option>
          <option value="2">难度 2</option>
          <option value="3">难度 3</option>
          <option value="4">难度 4</option>
          <option value="5">难度 5</option>
        </select>
        <select v-model="filters.sortMode" @change="runFilter">
          <option value="created_desc">时间：新到旧</option>
          <option value="created_asc">时间：旧到新</option>
          <option value="mastery_desc">掌握度：高到低</option>
          <option value="mastery_asc">掌握度：低到高</option>
        </select>
      </div>
      <div style="display: flex; gap: 8px;">
        <button @click="runFilter">刷新</button>
        <button @click="resetFilter">重置</button>
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

    <teleport to="body">
      <div
        v-if="showActionModal && selectedQuestion"
        style="position: fixed; inset: 0; z-index: 1200; background: rgba(17,24,39,0.36); display: grid; place-items: center;"
      >
        <div class="swift-card" style="width: 920px; max-width: 95vw; max-height: 88vh; overflow: auto; padding: 16px;">
          <h3 style="margin-top: 0;">题目详情与操作</h3>
          <p><strong>题目：</strong>{{ selectedQuestion.stem }}</p>
          <p><strong>参考答案：</strong>{{ selectedQuestion.reference_answer || "暂无" }}</p>

          <div style="display: flex; gap: 8px; margin: 10px 0;">
            <button @click="editing = true">编辑题目</button>
            <button @click="removeCurrent">删除题目</button>
            <button @click="loadRecords">查看做题记录</button>
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
            <h4 style="margin-bottom: 6px;">做题记录</h4>
            <div style="display: grid; gap: 8px;">
              <div v-for="r in records" :key="r.id" style="border: 1px solid #dde3ee; padding: 8px; border-radius: 10px;">
                <div><strong>评分：</strong>{{ r.ai_score }}/10</div>
                <div><strong>用户答案：</strong>{{ r.user_answer || "-" }}</div>
                <div><strong>AI答案：</strong>{{ r.ai_answer || "-" }}</div>
                <div style="font-size: 12px; color: #666;">时间：{{ r.created_at }}</div>
              </div>
              <p v-if="records.length === 0" style="color: #666;">暂无做题记录</p>
            </div>
          </div>

          <div style="margin-top: 12px;">
            <button @click="closeActionModal">关闭</button>
          </div>
        </div>
      </div>
    </teleport>
  </section>
</template>
