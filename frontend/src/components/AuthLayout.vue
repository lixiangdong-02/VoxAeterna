<script setup lang="ts">
import { computed } from 'vue'
import { useLocaleStore } from '@/stores/localeStore'
const localeStore = useLocaleStore()
const t = computed(() => localeStore.t)
</script>

<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-back" @click="$router.push('/')">{{ t.auth.back }}</div>
      <h1 class="auth-title"><slot name="title"></slot></h1>
      <p class="auth-sub"><slot name="subtitle"></slot></p>
      <slot></slot>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--c-bg);
}
.auth-card {
  width: 380px;
  padding: 40px 36px;
  background: var(--c-bg-elevated);
  border: 1px solid var(--c-border);
  border-radius: var(--radius-lg);
}
.auth-back {
  font-size: 12px;
  color: var(--c-text-secondary);
  cursor: pointer;
  margin-bottom: 24px;
  display: inline-block;
}
.auth-back:hover { color: var(--c-text); }
.auth-title {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin-bottom: 4px;
}
.auth-sub {
  font-size: 13px;
  color: var(--c-text-muted);
  margin-bottom: 28px;
}
</style>
