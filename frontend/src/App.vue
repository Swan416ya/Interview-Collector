<script setup lang="ts">
import {
  BookOpen,
  Brain,
  ClipboardList,
  FolderKanban,
  History,
  House,
  Sparkles,
  UploadCloud,
  UserCircle2
} from "lucide-vue-next";
import { mockUserProfile } from "./mock/userProfile";

const navItems = [
  { to: "/", title: "用户主页", desc: "个人信息、活跃图、每日一题", icon: House },
  { to: "/questions", title: "题库", desc: "筛选、排序、做题记录", icon: BookOpen },
  { to: "/copilot", title: "知识库", desc: "RAG 问答与引用", icon: Sparkles },
  { to: "/import", title: "导入", desc: "AI 提取并入库面经题目", icon: UploadCloud },
  { to: "/practice", title: "训练", desc: "刷题/背题均支持 5/10/15 题", icon: Brain },
  { to: "/practice-history", title: "刷题记录", desc: "查看每轮会话与得分", icon: History },
  { to: "/answer-records", title: "答题记录", desc: "全部作答行、与热力图对账", icon: ClipboardList },
  { to: "/categories", title: "分类/岗位", desc: "统一维护分类与岗位", icon: FolderKanban }
];
</script>

<template>
  <main class="swift-shell">
    <aside class="swift-sidebar">
      <router-link to="/" class="swift-profile">
        <img :src="mockUserProfile.avatarUrl" alt="avatar" />
        <div>
          <div style="font-weight: 700;">{{ mockUserProfile.username }}</div>
          <div style="font-size: 12px; color: #6b7280; display: flex; align-items: center; gap: 4px;">
            <UserCircle2 :size="14" /> UID {{ mockUserProfile.uid }}
          </div>
        </div>
      </router-link>

      <nav class="swift-nav">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="swift-nav-item"
          active-class="active"
        >
          <div class="swift-nav-title">
            <component :is="item.icon" :size="16" />
            <span>{{ item.title }}</span>
          </div>
          <div class="swift-nav-desc">{{ item.desc }}</div>
        </router-link>
      </nav>
    </aside>

    <section class="swift-content">
      <router-view />
    </section>
  </main>
</template>

