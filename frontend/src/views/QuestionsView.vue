<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { fetchCategories } from "../api/taxonomy";
import { fetchQuestionRecords, type PracticeRecord } from "../api/questions";
import { useQuestionStore } from "../stores/questionStore";

const store = useQuestionStore();

const form = reactive({
  stem: "",
  category: "未分类",
  difficulty: 3
});

const filters = reactive({
  category: "",
  difficulty: undefined as number | undefined
});
const categoryOptions = ref<string[]>([]);

const editingId = ref<number | null>(null);
const editForm = reactive({
  stem: "",
  category: "未分类",
  difficulty: 3
});
const showCreateModal = ref(false);
const showRecordsModal = ref(false);
const currentQuestionTitle = ref("");
const currentQuestionId = ref<number | null>(null);
const records = ref<PracticeRecord[]>([]);

const filteredMastery = ref(0);

function recalcMastery() {
  if (!store.items.length) {
    filteredMastery.value = 0;
    return;
  }
  const total = store.items.reduce((sum, q) => sum + (q.mastery_score ?? 0), 0);
  filteredMastery.value = Math.round(total / store.items.length);
}

async function submit() {
  if (form.stem.trim().length < 3) return;
  await store.addQuestion({
    stem: form.stem.trim(),
    category: form.category.trim() || "未分类",
    difficulty: Number(form.difficulty)
  });
  form.stem = "";
  showCreateModal.value = false;
  recalcMastery();
}

async function runFilter() {
  await store.loadQuestions({
    category: filters.category.trim() || undefined,
    difficulty: filters.difficulty || undefined
  });
  recalcMastery();
}

async function resetFilter() {
  filters.category = "";
  filters.difficulty = undefined;
  await store.loadQuestions();
  recalcMastery();
}

function startEdit(id: number, stem: string, category: string, difficulty: number) {
  editingId.value = id;
  editForm.stem = stem;
  editForm.category = category;
  editForm.difficulty = difficulty;
}

function cancelEdit() {
  editingId.value = null;
}

async function saveEdit(id: number) {
  if (editForm.stem.trim().length < 3) return;
  await store.editQuestion(id, {
    stem: editForm.stem.trim(),
    category: editForm.category.trim() || "未分类",
    difficulty: Number(editForm.difficulty)
  });
  editingId.value = null;
  await runFilter();
}

async function remove(id: number) {
  const yes = window.confirm("确认删除这道题吗？");
  if (!yes) return;
  await store.removeQuestion(id);
  await runFilter();
}

async function openRecords(id: number, stem: string) {
  currentQuestionId.value = id;
  currentQuestionTitle.value = stem;
  records.value = await fetchQuestionRecords(id);
  showRecordsModal.value = true;
}

onMounted(async () => {
  const cats = await fetchCategories();
  categoryOptions.value = cats.map((c) => c.name);
  await store.loadQuestions();
  recalcMastery();
});
</script>

<template>
  <section>
    <h2>题库管理</h2>
    <p>当前筛选结果题数：{{ store.items.length }}，总掌握程度：{{ filteredMastery }}%</p>

    <div style="margin-bottom: 12px;">
      <button @click="showCreateModal = true">新增题目</button>
    </div>

    <div style="display: grid; gap: 8px; margin-bottom: 16px; border: 1px solid #ddd; padding: 10px;">
      <h3 style="margin: 0;">筛选</h3>
      <select v-model="filters.category" @change="runFilter">
        <option value="">全部分类</option>
        <option v-for="c in categoryOptions" :key="c" :value="c">{{ c }}</option>
      </select>
      <select v-model.number="filters.difficulty" @change="runFilter">
        <option :value="undefined">全部难度</option>
        <option :value="1">难度 1</option>
        <option :value="2">难度 2</option>
        <option :value="3">难度 3</option>
        <option :value="4">难度 4</option>
        <option :value="5">难度 5</option>
      </select>
      <div style="display: flex; gap: 8px;">
        <button @click="resetFilter">重置</button>
      </div>
    </div>

    <p v-if="store.loading">加载中...</p>
    <div v-else style="display: grid; gap: 10px;">
      <div v-for="q in store.items" :key="q.id" style="border: 1px solid #ddd; padding: 10px; border-radius: 6px;">
        <template v-if="editingId === q.id">
          <textarea v-model="editForm.stem" rows="3" style="width: 100%;"></textarea>
          <input v-model="editForm.category" />
          <input v-model.number="editForm.difficulty" type="number" min="1" max="5" />
          <div style="display: flex; gap: 8px; margin-top: 8px;">
            <button @click="saveEdit(q.id)">保存</button>
            <button @click="cancelEdit">取消</button>
          </div>
        </template>
        <template v-else>
          <div>[{{ q.category }}][难度{{ q.difficulty }}] {{ q.stem }}</div>
          <div style="font-size: 12px; color: #2c7;">掌握程度：{{ q.mastery_score }}%</div>
          <div style="font-size: 12px; color: #666;">入库时间：{{ q.created_at }}</div>
          <div style="display: flex; gap: 8px; margin-top: 8px;">
            <button @click="openRecords(q.id, q.stem)">做题记录</button>
            <button @click="startEdit(q.id, q.stem, q.category, q.difficulty)">编辑</button>
            <button @click="remove(q.id)">删除</button>
          </div>
        </template>
      </div>
    </div>

    <div
      v-if="showCreateModal"
      style="position: fixed; inset: 0; background: rgba(0,0,0,0.35); display: grid; place-items: center;"
    >
      <div style="background: #fff; width: 680px; max-width: 92vw; padding: 16px; border-radius: 8px;">
        <h3>新增题目</h3>
        <div style="display: grid; gap: 8px; margin-bottom: 12px;">
          <textarea v-model="form.stem" rows="4" placeholder="输入题干"></textarea>
          <input v-model="form.category" placeholder="分类（如 计算机网络）" />
          <input v-model.number="form.difficulty" type="number" min="1" max="5" />
        </div>
        <div style="display: flex; gap: 8px;">
          <button @click="submit">保存</button>
          <button @click="showCreateModal = false">取消</button>
        </div>
      </div>
    </div>

    <div
      v-if="showRecordsModal"
      style="position: fixed; inset: 0; background: rgba(0,0,0,0.35); display: grid; place-items: center;"
    >
      <div style="background: #fff; width: 860px; max-width: 95vw; padding: 16px; border-radius: 8px;">
        <h3>做题记录：{{ currentQuestionTitle }}</h3>
        <p style="margin: 0 0 10px; color: #666;">记录由训练流程自动写入，此处仅查看。</p>
        <div style="max-height: 45vh; overflow: auto; display: grid; gap: 8px;">
          <div v-for="r in records" :key="r.id" style="border: 1px solid #ddd; padding: 8px; border-radius: 6px;">
            <div><strong>评分：</strong>{{ r.ai_score }}</div>
            <div><strong>用户答案：</strong>{{ r.user_answer || "-" }}</div>
            <div><strong>AI答案：</strong>{{ r.ai_answer || "-" }}</div>
            <div style="font-size: 12px; color: #666;">时间：{{ r.created_at }}</div>
          </div>
        </div>
        <div style="margin-top: 10px;">
          <button @click="showRecordsModal = false">关闭</button>
        </div>
      </div>
    </div>
  </section>
</template>

