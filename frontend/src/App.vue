<template>
  <main style="max-width: 960px; margin: 40px auto; font-family: Arial, sans-serif;">
    <h1>Interview Collector</h1>
    <nav style="display: flex; gap: 12px; margin: 12px 0 20px;">
      <router-link to="/">首页</router-link>
      <router-link to="/questions">题库</router-link>
      <router-link to="/categories">分类</router-link>
      <router-link to="/roles">岗位</router-link>
      <router-link to="/import">导入</router-link>
      <router-link to="/practice">训练</router-link>
    </nav>
    <router-view />
  </main>
</template>

