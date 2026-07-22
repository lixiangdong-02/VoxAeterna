<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import { useLocaleStore } from '@/stores/localeStore'
import { useUserStore } from '@/stores/userStore'
import { cloudApi } from '@/api'

const emit = defineEmits<{ close: [] }>()
const localeStore = useLocaleStore()
const userStore = useUserStore()
const t = computed(() => localeStore.t)
const _ = localeStore._

const plans = [
  { key: 'monthly', name: t.value.upgrade.monthly, price: t.value.upgrade.priceMonthly, per: t.value.upgrade.perMonth, features: [t.value.upgrade.featureUnlimited, t.value.upgrade.featureExport] },
  { key: 'yearly', name: t.value.upgrade.yearly, price: t.value.upgrade.priceYearly, per: t.value.upgrade.perYear, features: [t.value.upgrade.featureUnlimited, t.value.upgrade.featureExport, t.value.upgrade.featurePriority] },
  { key: 'lifetime', name: t.value.upgrade.lifetime, price: t.value.upgrade.priceLifetime, per: t.value.upgrade.oneTime, features: [t.value.upgrade.featureUnlimited, t.value.upgrade.featureExport, t.value.upgrade.featurePriority] },
]

// State machine: 'plans' | 'paying' | 'success' | 'failed'
const screen = ref<'plans' | 'paying' | 'success' | 'failed'>('plans')
const selectedPlan = ref('')
const loading = ref(false)
const errorMsg = ref('')

// Order state
const orderId = ref(0)
const qrcodeUrl = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

async function selectPlan(planKey: string) {
  selectedPlan.value = planKey
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await cloudApi.createOrder(planKey)
    const data = res.data
    orderId.value = data.order_id
    qrcodeUrl.value = data.qrcode_url || ''
    screen.value = 'paying'
    startPolling()
  } catch (e: any) {
    errorMsg.value = e.response?.data?.detail || t.value.upgrade.payFailed
  } finally {
    loading.value = false
  }
}

function startPolling() {
  pollTimer = setInterval(async () => {
    try {
      const res = await cloudApi.getOrderStatus(orderId.value)
      const status = res.data.status
      if (status === 'paid') {
        if (pollTimer) clearInterval(pollTimer)
        pollTimer = null
        screen.value = 'success'
        await userStore.fetchStatus()
        setTimeout(() => emit('close'), 3000)
      } else if (status === 'cancelled') {
        if (pollTimer) clearInterval(pollTimer)
        pollTimer = null
        screen.value = 'failed'
        errorMsg.value = t.value.upgrade.payCancelled
      }
    } catch {
      // Continue polling
    }
  }, 2000)
}

function goBack() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = null
  screen.value = 'plans'
  errorMsg.value = ''
}

function close() {
  if (pollTimer) clearInterval(pollTimer)
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div class="modal-overlay" @click.self="close">
      <div class="modal-card">
        <!-- Header -->
        <div class="modal-header">
          <h2>{{ t.upgrade.title }}</h2>
          <button class="btn-close" @click="close">&times;</button>
        </div>

        <!-- Plans Screen -->
        <template v-if="screen === 'plans'">
          <p class="modal-subtitle">{{ t.upgrade.subtitle }}</p>
          <div class="plans-grid">
            <div
              v-for="plan in plans"
              :key="plan.key"
              class="plan-card"
              :class="{ selected: selectedPlan === plan.key }"
            >
              <div class="plan-name">{{ plan.name }}</div>
              <div class="plan-price">
                <span class="plan-amount">{{ plan.price }}</span>
                <span class="plan-per">{{ plan.per }}</span>
              </div>
              <ul class="plan-features">
                <li v-for="f in plan.features" :key="f">✓ {{ f }}</li>
              </ul>
              <button
                class="btn"
                :class="selectedPlan === plan.key ? 'btn-primary' : 'btn-ghost'"
                :disabled="loading"
                @click="selectPlan(plan.key)"
              >
                {{ loading && selectedPlan === plan.key ? t.upgrade.paying : t.upgrade.choosePlan }}
              </button>
            </div>
          </div>
          <p v-if="errorMsg" class="err-text">{{ errorMsg }}</p>
        </template>

        <!-- Paying Screen -->
        <template v-if="screen === 'paying'">
          <p class="modal-subtitle">{{ t.upgrade.scanToPay }}</p>
          <div class="qrcode-box">
            <template v-if="qrcodeUrl">
              <img :src="qrcodeUrl" alt="Payment QR Code" class="qr-img" />
            </template>
            <template v-else>
              <div class="qr-placeholder">
                <div class="qr-icon">📱</div>
                <p class="qr-hint">{{ t.upgrade.scanToPay }}</p>
                <p class="qr-dev-hint">开发模式：配置 PAYJS 后将显示支付二维码</p>
              </div>
            </template>
          </div>
          <p class="paying-text">{{ t.upgrade.paying }}</p>
          <button class="btn btn-ghost btn-back" @click="goBack">{{ t.upgrade.back }}</button>
        </template>

        <!-- Success Screen -->
        <template v-if="screen === 'success'">
          <div class="result-box success">
            <div class="result-icon">✓</div>
            <p class="result-text">{{ t.upgrade.paySuccess }}</p>
          </div>
        </template>

        <!-- Failed Screen -->
        <template v-if="screen === 'failed'">
          <div class="result-box failed">
            <div class="result-icon">✗</div>
            <p class="result-text">{{ errorMsg || t.upgrade.payFailed }}</p>
            <button class="btn btn-primary" @click="goBack">{{ t.upgrade.back }}</button>
          </div>
        </template>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal-card {
  background: var(--c-bg-elevated);
  border: 1px solid var(--c-border);
  border-radius: var(--radius-lg);
  padding: 32px;
  width: 720px;
  max-width: 92vw;
  max-height: 90vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.modal-header h2 {
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 700;
  color: var(--c-text);
}
.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  color: var(--c-text-muted);
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
}
.btn-close:hover { background: var(--c-bg-glass); color: var(--c-text); }
.modal-subtitle {
  font-size: 14px;
  color: var(--c-text-secondary);
  text-align: center;
  margin-top: -8px;
}

.plans-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
.plan-card {
  background: var(--c-bg);
  border: 2px solid var(--c-border);
  border-radius: var(--radius-md);
  padding: 24px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  text-align: center;
  transition: border-color var(--duration-fast), box-shadow var(--duration-fast);
  cursor: pointer;
}
.plan-card:hover { border-color: var(--c-accent-bg-hover); }
.plan-card.selected { border-color: var(--c-accent); box-shadow: 0 0 0 3px var(--c-accent-bg); }
.plan-name { font-size: 14px; font-weight: 600; color: var(--c-text); }
.plan-amount { font-size: 28px; font-weight: 700; color: var(--c-accent); font-family: var(--font-display); }
.plan-per { font-size: 12px; color: var(--c-text-muted); }
.plan-features {
  list-style: none;
  padding: 0;
  margin: 0;
  font-size: 12px;
  color: var(--c-text-secondary);
  text-align: left;
}
.plan-features li { padding: 3px 0; }

.qrcode-box {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: white;
  border-radius: var(--radius-md);
  min-height: 280px;
}
.qr-img { width: 240px; height: 240px; }
.qr-placeholder { text-align: center; }
.qr-icon { font-size: 48px; margin-bottom: 12px; }
.qr-hint { font-size: 14px; color: #333; }
.qr-dev-hint { font-size: 11px; color: #999; margin-top: 8px; }
.paying-text {
  font-size: 13px;
  color: var(--c-text-muted);
  text-align: center;
}
.btn-back {
  width: 100%;
  justify-content: center;
}

.result-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 32px 0;
}
.result-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 700;
}
.success .result-icon { background: var(--c-accent-bg); color: var(--c-accent); }
.failed .result-icon { background: var(--c-danger-bg); color: var(--c-danger); }
.result-text { font-size: 15px; color: var(--c-text); }

.err-text { font-size: 13px; color: var(--c-danger); text-align: center; }

@media (max-width: 640px) {
  .plans-grid { grid-template-columns: 1fr; }
}
</style>
