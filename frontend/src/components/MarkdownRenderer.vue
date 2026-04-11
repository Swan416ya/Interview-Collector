<script setup lang="ts">
import DOMPurify from "dompurify";
import { marked } from "marked";
import { computed } from "vue";

marked.use({
  gfm: true,
  breaks: true
});

const props = withDefaults(
  defineProps<{
    /** Markdown source; empty renders nothing */
    source?: string | null;
  }>(),
  { source: "" }
);

const html = computed(() => {
  const s = (props.source ?? "").trim();
  if (!s) return "";
  const raw = marked.parse(s) as string;
  return DOMPurify.sanitize(raw);
});
</script>

<template>
  <div v-if="html" class="ic-md" v-html="html" />
</template>

<style scoped>
.ic-md {
  font-size: 0.95rem;
  line-height: 1.55;
  color: var(--swift-text, #111827);
}

.ic-md :deep(h1),
.ic-md :deep(h2),
.ic-md :deep(h3),
.ic-md :deep(h4) {
  margin: 0.65em 0 0.35em;
  font-weight: 700;
  line-height: 1.35;
}

.ic-md :deep(h1) {
  font-size: 1.15em;
}

.ic-md :deep(h2) {
  font-size: 1.08em;
}

.ic-md :deep(h3),
.ic-md :deep(h4) {
  font-size: 1.02em;
}

.ic-md :deep(p) {
  margin: 0.45em 0;
}

.ic-md :deep(ul),
.ic-md :deep(ol) {
  margin: 0.4em 0;
  padding-left: 1.35em;
}

.ic-md :deep(li) {
  margin: 0.2em 0;
}

.ic-md :deep(pre) {
  margin: 0.5em 0;
  padding: 10px 12px;
  background: #f1f5f9;
  border-radius: 10px;
  overflow-x: auto;
  font-size: 0.88em;
}

.ic-md :deep(code) {
  padding: 0.1em 0.4em;
  background: rgba(15, 23, 42, 0.06);
  border-radius: 5px;
  font-size: 0.9em;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

.ic-md :deep(pre code) {
  padding: 0;
  background: none;
  font-size: inherit;
}

.ic-md :deep(blockquote) {
  margin: 0.5em 0;
  padding: 0.35em 0 0.35em 0.9em;
  border-left: 3px solid #cbd5e1;
  color: #475569;
}

.ic-md :deep(a) {
  color: var(--swift-primary, #2563eb);
  text-decoration: underline;
}

.ic-md :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 0.5em 0;
  font-size: 0.92em;
}

.ic-md :deep(th),
.ic-md :deep(td) {
  border: 1px solid #e2e8f0;
  padding: 6px 10px;
  text-align: left;
}

.ic-md :deep(hr) {
  border: none;
  border-top: 1px solid #e5e7eb;
  margin: 0.85em 0;
}
</style>
