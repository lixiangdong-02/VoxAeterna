import { ref, watch } from 'vue'
import { defineStore } from 'pinia'

export type ThemeMode = 'dark' | 'light'

export const useThemeStore = defineStore('theme', () => {
  const saved = (localStorage.getItem('vox_theme') as ThemeMode) || 'dark'
  const mode = ref<ThemeMode>(saved)

  function apply(m: ThemeMode) {
    document.documentElement.setAttribute('data-theme', m)
    document.documentElement.style.setProperty('color-scheme', m)
  }

  // 初始化
  apply(mode.value)

  watch(mode, (m) => {
    localStorage.setItem('vox_theme', m)
    apply(m)
  })

  function toggle() {
    mode.value = mode.value === 'dark' ? 'light' : 'dark'
  }

  return { mode, toggle }
})
