<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useThemeStore } from '@/stores/themeStore'
import { useLocaleStore } from '@/stores/localeStore'

const isMaximized = ref(false)
const winControls = (window as any).windowControls
const themeStore = useThemeStore()
const localeStore = useLocaleStore()
const t = computed(() => localeStore.t)

onMounted(() => {
  if (winControls) {
    winControls.isMaximized().then((v: boolean) => (isMaximized.value = v))
    winControls.onMaximizeChange((v: boolean) => (isMaximized.value = v))
  }
})

function onMinimize() {
  winControls?.minimize()
}
function onMaximize() {
  winControls?.maximize()
}
function onClose() {
  winControls?.close()
}
</script>

<template>
  <header class="titlebar">
    <div class="titlebar-drag">
      <img src="/icon.png" alt="" class="titlebar-icon" />
      <span class="titlebar-title">VoxAeterna</span>
    </div>
    <div class="titlebar-controls">
      <button class="tb-btn tb-locale" @click="localeStore.toggle()" :title="localeStore.locale === 'zh' ? 'Switch to English' : '切换为中文'">
        <span class="locale-label">{{ localeStore.locale === 'zh' ? 'EN' : '中' }}</span>
      </button>
      <button class="tb-btn tb-theme" @click="themeStore.toggle()" :title="themeStore.mode === 'dark' ? t.titlebar.switchLight : t.titlebar.switchDark">
        <svg v-if="themeStore.mode === 'dark'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
        </svg>
        <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
        </svg>
      </button>
      <button class="tb-btn tb-min" @click="onMinimize" :title="t.titlebar.minimize">
        <svg width="12" height="12" viewBox="0 0 12 12"><rect y="5" width="12" height="1.5" rx="0.75" fill="currentColor"/></svg>
      </button>
      <button class="tb-btn tb-max" @click="onMaximize" :title="isMaximized ? t.titlebar.restore : t.titlebar.maximize">
        <svg v-if="isMaximized" width="12" height="12" viewBox="0 0 12 12">
          <rect x="3" y="0" width="9" height="9" rx="1" fill="none" stroke="currentColor" stroke-width="1.3"/>
          <rect x="0" y="3" width="9" height="9" rx="1" fill="none" stroke="currentColor" stroke-width="1.3"/>
          <rect x="2" y="2.5" width="7" height="7" rx="0.5" fill="var(--c-titlebar-fill)"/>
        </svg>
        <svg v-else width="12" height="12" viewBox="0 0 12 12">
          <rect x="0.5" y="0.5" width="11" height="11" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.3"/>
        </svg>
      </button>
      <button class="tb-btn tb-close" @click="onClose" :title="t.titlebar.close">
        <svg width="12" height="12" viewBox="0 0 12 12">
          <path d="M1 1l10 10M11 1L1 11" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </button>
    </div>
  </header>
</template>

<style scoped>
.titlebar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 36px;
  background: var(--c-titlebar-bg);
  border-bottom: 1px solid var(--c-border);
  flex-shrink: 0;
  z-index: 1000;
}

.titlebar-drag {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-left: 12px;
  flex: 1;
  height: 100%;
  -webkit-app-region: drag;
}

.titlebar-icon {
  width: 16px;
  height: 16px;
  border-radius: 3px;
  flex-shrink: 0;
}

.titlebar-title {
  font-family: var(--font-display, 'Microsoft YaHei', sans-serif);
  font-size: 11px;
  font-weight: 600;
  color: var(--c-text-secondary);
  letter-spacing: 0.03em;
}

.titlebar-controls {
  display: flex;
  height: 100%;
  -webkit-app-region: no-drag;
}

.tb-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 100%;
  border: none;
  background: transparent;
  color: var(--c-text-secondary);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.locale-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
}

.tb-locale:hover .locale-label {
  color: var(--c-accent);
}

.tb-btn:hover {
  background: var(--c-bg-glass-hover);
  color: var(--c-text);
}

.tb-close:hover {
  background: var(--c-danger);
  color: #fff;
}
</style>
