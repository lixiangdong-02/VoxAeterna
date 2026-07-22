import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { zh } from '@/i18n/zh'
import { en } from '@/i18n/en'
import type { LocaleMessages } from '@/i18n/zh'

export type Locale = 'zh' | 'en'

const messages: Record<Locale, LocaleMessages> = { zh, en }

export const useLocaleStore = defineStore('locale', () => {
  const saved = (localStorage.getItem('vox_locale') as Locale) || 'zh'
  const locale = ref<Locale>(saved)

  const t = computed(() => messages[locale.value])

  function setLocale(l: Locale) {
    locale.value = l
    localStorage.setItem('vox_locale', l)
    document.documentElement.setAttribute('lang', l)
  }

  function toggle() {
    setLocale(locale.value === 'zh' ? 'en' : 'zh')
  }

  // 提供模板插值工具
  function _(key: string, params?: Record<string, string | number>): string {
    const keys = key.split('.')
    let val: any = t.value
    for (const k of keys) {
      val = val?.[k]
    }
    if (typeof val !== 'string') return key
    if (!params) return val
    return val.replace(/\{(\w+)\}/g, (_, k) => String(params[k] ?? `{${k}}`))
  }

  return { locale, t, setLocale, toggle, _ }
})
