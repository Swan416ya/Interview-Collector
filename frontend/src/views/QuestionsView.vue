<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { useQuestionStore } from "../stores/questionStore";

const store = useQuestionStore();

const form = reactive({
  stem: "",
  category: "未分类",
  difficulty: 3
});

const filters = reactive({
  category: "",
  keyword: "",
  difficulty: undefined as number | undefined
});

const editingId = ref<number | null>(null);
const editForm = reactive({
  stem: "",
  category: "未分类",
  difficulty: 3
});

async function submit() {
  if (form.stem.trim().length < 3) return;
  await store.addQuestion({
    stem: form.stem.trim(),
    category: form.category.trim() || "未分类",
    difficulty: Number(form.difficulty)
  });
  form.stem = "";
}

async function runFilter() {
  await store.loadQuestions({
    category: filters.category.trim() || undefined,
    keyword: filters.keyword.trim() || undefined,
    difficulty: filters.difficulty || undefined
  });
}

async function resetFilter() {
  filters.category = "";
  filters.keyword = "";
  filters.difficulty = undefined;
  await store.loadQuestions();
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
}

async function remove(id: number) {
  const yes = window.confirm("确认删除这道题吗？");
  if (!yes) return;
  await store.removeQuestion(id);
}

onMounted(async () => {
  await store.loadQuestions();
});
</script>

<template>
  <section>
    <h2>题库管理</h2>

    <div style="display: grid; gap: 8px; margin-bottom: 16px;">
      <textarea v-model="form.stem" rows="4" placeholder="输入题干"></textarea>
      <input v-model="form.category" placeholder="分类（如 计算机网络）" />
      <input v-model.number="form.difficulty" type="number" min="1" max="5" />
      <button @click="submit">新增题目</button>
    </div>

    <div style="display: grid; gap: 8px; margin-bottom: 16px; border: 1px solid #ddd; padding: 10px;">
      <h3 style="margin: 0;">筛选</h3>
      <input v-model="filters.keyword" placeholder="关键词（题干）" />
      <input v-model="filters.category" placeholder="分类筛选" />
      <input v-model.number="filters.difficulty" type="number" min="1" max="5" placeholder="难度筛选" />
      <div style="display: flex; gap: 8px;">
        <button @click="runFilter">查询</button>
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
          <div style="font-size: 12px; color: #666;">入库时间：{{ q.created_at }}</div>
          <div style="display: flex; gap: 8px; margin-top: 8px;">
            <button @click="startEdit(q.id, q.stem, q.category, q.difficulty)">编辑</button>
            <button @click="remove(q.id)">删除</button>
          </div>
        </template>
      </div>
    </div>
  </section>
</template>

