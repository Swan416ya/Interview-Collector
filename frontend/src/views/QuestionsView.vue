<script setup lang="ts">
import { onMounted, reactive } from "vue";
import { useQuestionStore } from "../stores/questionStore";

const store = useQuestionStore();

const form = reactive({
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

    <p v-if="store.loading">加载中...</p>
    <ul v-else>
      <li v-for="q in store.items" :key="q.id">
        [{{ q.category }}][难度{{ q.difficulty }}] {{ q.stem }}
      </li>
    </ul>
  </section>
</template>

