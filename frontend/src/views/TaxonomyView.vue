<script setup lang="ts">
import { onMounted, ref } from "vue";
import {
  createCategory,
  createRole,
  fetchCategories,
  fetchRoles,
  type NamedEntity
} from "../api/taxonomy";

const loading = ref(false);
const error = ref("");

const categories = ref<NamedEntity[]>([]);
const roles = ref<NamedEntity[]>([]);

const categoryName = ref("");
const roleName = ref("");

async function loadAll() {
  loading.value = true;
  error.value = "";
  try {
    const [cats, rs] = await Promise.all([fetchCategories(), fetchRoles()]);
    categories.value = cats;
    roles.value = rs;
  } catch (e) {
    error.value = "加载分类/岗位失败";
  } finally {
    loading.value = false;
  }
}

async function addCategory() {
  const v = categoryName.value.trim();
  if (!v) return;
  error.value = "";
  try {
    await createCategory(v);
    categoryName.value = "";
    await loadAll();
  } catch (e) {
    error.value = "新增分类失败（可能重名）";
  }
}

async function addRole() {
  const v = roleName.value.trim();
  if (!v) return;
  error.value = "";
  try {
    await createRole(v);
    roleName.value = "";
    await loadAll();
  } catch (e) {
    error.value = "新增岗位失败（可能重名）";
  }
}

onMounted(loadAll);
</script>

<template>
  <section>
    <h2>分类与岗位管理</h2>
    <p v-if="error" style="color: #c0392b;">{{ error }}</p>
    <p v-if="loading">加载中...</p>

    <div v-else style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
      <div class="swift-card">
        <h3 style="margin-top: 0;">分类</h3>
        <div style="display: flex; gap: 8px; margin-bottom: 12px;">
          <input v-model="categoryName" placeholder="例如：计算机网络" />
          <button @click="addCategory">新增</button>
          <button @click="loadAll">刷新</button>
        </div>
        <ul style="margin: 0; padding-left: 18px;">
          <li v-for="item in categories" :key="item.id">{{ item.name }}</li>
        </ul>
      </div>

      <div class="swift-card">
        <h3 style="margin-top: 0;">岗位</h3>
        <div style="display: flex; gap: 8px; margin-bottom: 12px;">
          <input v-model="roleName" placeholder="例如：后端" />
          <button @click="addRole">新增</button>
          <button @click="loadAll">刷新</button>
        </div>
        <ul style="margin: 0; padding-left: 18px;">
          <li v-for="item in roles" :key="item.id">{{ item.name }}</li>
        </ul>
      </div>
    </div>
  </section>
</template>
