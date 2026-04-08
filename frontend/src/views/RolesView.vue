<script setup lang="ts">
import { onMounted, ref } from "vue";
import { createRole, fetchRoles, type NamedEntity } from "../api/taxonomy";

const loading = ref(false);
const name = ref("");
const items = ref<NamedEntity[]>([]);
const error = ref("");

async function load() {
  loading.value = true;
  error.value = "";
  try {
    items.value = await fetchRoles();
  } catch (e) {
    error.value = "加载岗位失败";
  } finally {
    loading.value = false;
  }
}

async function submit() {
  const v = name.value.trim();
  if (!v) return;
  error.value = "";
  try {
    await createRole(v);
    name.value = "";
    await load();
  } catch (e) {
    error.value = "新增失败（可能重名）";
  }
}

onMounted(load);
</script>

<template>
  <section>
    <h2>岗位管理</h2>
    <div style="display: flex; gap: 8px; margin-bottom: 12px;">
      <input v-model="name" placeholder="例如：后端" />
      <button @click="submit">新增岗位</button>
      <button @click="load">刷新</button>
    </div>
    <p v-if="error" style="color: #c0392b;">{{ error }}</p>
    <p v-if="loading">加载中...</p>
    <ul v-else>
      <li v-for="item in items" :key="item.id">{{ item.name }}</li>
    </ul>
  </section>
</template>

