import { defineStore } from 'pinia'
import { ref } from 'vue'
import { cloudApi } from '@/api'
import type { SubscriptionStatus, UsageStats } from '@/types'

export const useUserStore = defineStore('user', () => {
  const trialRemaining = ref<number | null>(null)
  const subscriptionPlan = ref<string>('free')
  const subscriptionStatus = ref<string>('active')
  const subscriptionExpiresAt = ref<string | null>(null)
  const subscriptionStartsAt = ref<string | null>(null)
  const autoRenew = ref(false)
  const isLoading = ref(false)
  const usageStats = ref<UsageStats | null>(null)

  async function fetchStatus() {
    isLoading.value = true
    try {
      const [trialRes, subRes] = await Promise.all([
        cloudApi.trialStatus(),
        cloudApi.subscriptionStatus(),
      ])
      trialRemaining.value = trialRes.data.remaining
      subscriptionPlan.value = subRes.data.plan
      subscriptionStatus.value = subRes.data.status
      subscriptionExpiresAt.value = subRes.data.expires_at || null
      subscriptionStartsAt.value = subRes.data.starts_at || null
      autoRenew.value = subRes.data.auto_renew || false
    } catch {
      // 云服务不可用时静默降级
    } finally {
      isLoading.value = false
    }
  }

  async function fetchUsageStats() {
    try {
      const res = await cloudApi.getUsageStats()
      usageStats.value = res.data
    } catch { /* ignore */ }
  }

  const isConsuming = ref(false)  // 防重入锁

  async function consumeTrial(): Promise<boolean> {
    if (subscriptionPlan.value !== 'free') return true
    if (isConsuming.value) {
      console.warn('[trial] consumeTrial 已在进行中，跳过重复调用')
      return false
    }
    isConsuming.value = true
    try {
      const res = await cloudApi.consumeTrial()
      console.log('[trial] consumeTrial 响应:', res.data)
      trialRemaining.value = res.data.remaining
      return res.data.can_use !== false
    } catch (e: any) {
      console.error('[trial] consumeTrial 失败:', e?.response?.status, e?.response?.data || e?.message || e)
      return false
    } finally {
      isConsuming.value = false
    }
  }

  return {
    trialRemaining, subscriptionPlan, subscriptionStatus,
    subscriptionExpiresAt, subscriptionStartsAt, autoRenew,
    isLoading, usageStats,
    fetchStatus, fetchUsageStats, consumeTrial,
  }
})
