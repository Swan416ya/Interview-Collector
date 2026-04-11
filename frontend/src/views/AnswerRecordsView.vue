<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import MarkdownRenderer from "../components/MarkdownRenderer.vue";
import { fetchPracticeRecordFeed, type PracticeRecordFeedItem } from "../api/practice";

const loading = ref(false);
const error = ref("");
const total = ref(0);
const items = ref<PracticeRecordFeedItem[]>([]);

const pager = reactive({ page: 1, pageSize: 25 });
/** YYYY-MM-DD, empty = all days */
const shanghaiDate = ref("");

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pager.pageSize)));

function recordSourceLabel(r: PracticeRecordFeedItem): string {
  if (r.session_id == null) return "每日一题 / 无会话";
  return `训练会话 #${r.session_id}`;
}

function preview(text: string, max = 120): string {
  const t = (text ?? "").replace(/\s+/g, " ").trim();
  if (t.length <= max) return t || "—";
  return t.slice(0, max) + "…";
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const data = await fetchPracticeRecordFeed({
      page: pager.page,
      page_size: pager.pageSize,
      shanghai_date: shanghaiDate.value.trim() || undefined
    });
    total.value = data.total;
    items.value = data.items;
  } catch {
    error.value = "加载答题记录失败";
    total.value = 0;
    items.value = [];
  } finally {
    loading.value = false;
  }
}

function applyFilter() {
  pager.page = 1;
  load();
}

function goPage(p: number) {
  pager.page = Math.max(1, Math.min(totalPages.value, p));
  load();
}

const expandedId = ref<number | null>(null);

onMounted(load);
</script>

<template>
  <section>
    <h2>答题记录</h2>

    <div class="swift-card note-box">
      <h3 class="note-title">和「做题热力图」对不上时，先看这里</h3>
      <ul class="note-list">
        <li>
          <strong>统计的是什么：</strong>接口 <code>/api/practice/activity</code> 数的是
          <code>practice_records</code> 表的<strong>行数</strong>——训练里每答一题、每跳过一题、每日一题提交，各产生
          <strong>一行</strong>。同一道题当天做两次会算 <strong>两条</strong>，不是「去重后的题数」。
        </li>
        <li>
          <strong>按哪一天算：</strong>热力图按 <strong>Asia/Shanghai（上海）</strong>的日历日，把每条记录的
          <code>created_at</code> 归到某一天。数据库里若存的是「naive UTC」（推荐），后端会先当 UTC 再换到上海日期；若库里实际是别的时区的本地时间却未带时区，换日时可能<strong>和直觉差一天</strong>。
        </li>
        <li>
          <strong>时间窗口：</strong>热力图只展示最近 <strong>53 周</strong>格子；更早的记录不会出现在格子里，但本页可以翻到（未删库的话）。
        </li>
        <li>
          <strong>自查：</strong>在下面选一个「上海日期」筛选，本页<strong>总条数</strong>应与主页热力图<strong>同一天格子上的数字</strong>一致（同一天、同一套时区规则）。
        </li>
      </ul>
    </div>

    <div class="swift-card filter-row">
      <label class="filter-label">
        按上海日历日筛选
        <input v-model="shanghaiDate" type="date" class="filter-input" />
      </label>
      <button type="button" @click="applyFilter">应用</button>
      <button type="button" class="btn-ghost" @click="shanghaiDate = ''; applyFilter()">清除日期</button>
      <span v-if="!loading" class="filter-meta">
        共 <strong>{{ total }}</strong> 条
        <template v-if="shanghaiDate.trim()">（与热力图该日 count 应对齐）</template>
      </span>
    </div>

    <p v-if="error" class="err">{{ error }}</p>
    <p v-else-if="loading">加载中...</p>

    <div v-else-if="!items.length" class="swift-card empty">暂无记录</div>

    <div v-else class="table-wrap swift-card">
      <table class="rec-table">
        <thead>
          <tr>
            <th>时间</th>
            <th>来源</th>
            <th>题目</th>
            <th>得分</th>
            <th />
          </tr>
        </thead>
        <tbody>
          <template v-for="r in items" :key="r.id">
            <tr>
              <td class="td-time">{{ r.created_at }}</td>
              <td>{{ recordSourceLabel(r) }}</td>
              <td class="td-stem">{{ preview(r.question_stem, 80) }}</td>
              <td>{{ r.ai_score }}/10</td>
              <td>
                <button type="button" class="btn-link" @click="expandedId = expandedId === r.id ? null : r.id">
                  {{ expandedId === r.id ? "收起" : "详情" }}
                </button>
              </td>
            </tr>
            <tr v-if="expandedId === r.id" class="detail-row">
              <td colspan="5">
                <div class="detail-inner">
                  <p><strong>完整题干：</strong>{{ r.question_stem }}</p>
                  <p><strong>作答：</strong>{{ r.user_answer || "（空，可能为跳过）" }}</p>
                  <div>
                    <strong>AI 解析：</strong>
                    <MarkdownRenderer :source="r.ai_answer?.trim() ? r.ai_answer : '-'" />
                  </div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <div v-if="!loading && items.length" class="pager">
      <button type="button" :disabled="pager.page <= 1" @click="goPage(pager.page - 1)">上一页</button>
      <span>第 {{ pager.page }} / {{ totalPages }} 页</span>
      <button type="button" :disabled="pager.page >= totalPages" @click="goPage(pager.page + 1)">下一页</button>
      <select v-model.number="pager.pageSize" class="page-size" @change="applyFilter">
        <option :value="15">每页 15</option>
        <option :value="25">每页 25</option>
        <option :value="50">每页 50</option>
      </select>
    </div>
  </section>
</template>

<style scoped>
.note-box {
  margin-bottom: 14px;
  padding: 14px 16px;
}

.note-title {
  margin: 0 0 8px;
  font-size: 15px;
}

.note-list {
  margin: 0;
  padding-left: 1.25rem;
  font-size: 13px;
  color: #374151;
  line-height: 1.55;
}

.note-list li {
  margin-bottom: 6px;
}

.note-list code {
  font-size: 12px;
  padding: 1px 5px;
  border-radius: 4px;
  background: #f3f4f6;
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  padding: 12px;
}

.filter-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.filter-input {
  padding: 6px 8px;
  border-radius: 8px;
  border: 1px solid #d1d5db;
}

.filter-meta {
  font-size: 13px;
  color: #6b7280;
  margin-left: auto;
}

.btn-ghost {
  background: transparent;
  border: 1px solid #d1d5db;
}

.err {
  color: #c0392b;
}

.empty {
  padding: 16px;
}

.table-wrap {
  padding: 0;
  overflow-x: auto;
}

.rec-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.rec-table th,
.rec-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
  vertical-align: top;
}

.rec-table th {
  background: #f9fafb;
  font-weight: 600;
}

.td-time {
  white-space: nowrap;
  color: #6b7280;
  font-size: 12px;
}

.td-stem {
  max-width: 360px;
}

.detail-row td {
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}

.detail-inner {
  padding: 8px 0 12px;
  font-size: 13px;
  line-height: 1.5;
}

.btn-link {
  background: none;
  border: none;
  color: #0969da;
  cursor: pointer;
  padding: 0;
  font-size: 13px;
}

.btn-link:hover {
  text-decoration: underline;
}

.pager {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
  flex-wrap: wrap;
}

.page-size {
  margin-left: auto;
  padding: 6px 8px;
  border-radius: 8px;
}
</style>
