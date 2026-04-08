<template>
  <div class="ai-loader-wrap" role="status" aria-live="polite">
    <div class="ai-loader">
      <span></span>
      <span></span>
      <span></span>
    </div>
    <p>{{ text }}</p>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    text?: string;
  }>(),
  {
    text: "AI 正在处理中..."
  }
);
</script>

<style scoped>
.ai-loader-wrap {
  display: grid;
  place-items: center;
  gap: 10px;
  padding: 12px;
}

.ai-loader {
  width: 88px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ai-loader span {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: linear-gradient(180deg, #bcd7ff, #7eb1ff);
  box-shadow: 0 2px 10px rgba(37, 99, 235, 0.28);
  animation: hop 0.85s ease-in-out infinite;
}

.ai-loader span:nth-child(2) {
  animation-delay: 0.12s;
}

.ai-loader span:nth-child(3) {
  animation-delay: 0.24s;
}

@keyframes hop {
  0%,
  100% {
    transform: translateY(0);
    opacity: 0.8;
  }
  50% {
    transform: translateY(-9px);
    opacity: 1;
  }
}

p {
  margin: 0;
  color: #5b6576;
  font-size: 13px;
}
</style>
