<script setup lang="ts">
import { ref, computed, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useLocaleStore } from '@/stores/localeStore'
import { authApi } from '@/api'
import AuthLayout from '@/components/AuthLayout.vue'

const router = useRouter()
const localeStore = useLocaleStore()
const t = computed(() => localeStore.t)
const _ = localeStore._

// Step: 'email' | 'reset'
const step = ref<'email' | 'reset'>('email')

// Step 1: Enter email
const email = ref('')
const sending = ref(false)
const sentErr = ref('')

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

async function doSendCode() {
  if (!EMAIL_RE.test(email.value.trim())) {
    sentErr.value = t.value.auth.emailFormatError
    return
  }
  sending.value = true
  sentErr.value = ''
  try {
    await authApi.forgotPassword(email.value.trim().toLowerCase())
    step.value = 'reset'
  } catch (e: any) {
    sentErr.value = e.response?.data?.detail || '发送失败'
  } finally {
    sending.value = false
  }
}

// Step 2: Enter code + new password
const code = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const resetting = ref(false)
const resetErr = ref('')
const resetOk = ref(false)
const cooldown = ref(0)
let cooldownTimer: ReturnType<typeof setInterval> | null = null

function startCooldown() {
  if (cooldownTimer) clearInterval(cooldownTimer)
  cooldown.value = 60
  cooldownTimer = setInterval(() => {
    cooldown.value--
    if (cooldown.value <= 0) {
      if (cooldownTimer) clearInterval(cooldownTimer)
      cooldownTimer = null
    }
  }, 1000)
}

function clearCooldown() {
  if (cooldownTimer) clearInterval(cooldownTimer)
  cooldownTimer = null
  cooldown.value = 0
}

watch(step, (val) => {
  if (val === 'reset') startCooldown()
})

onUnmounted(() => clearCooldown())

async function doReset() {
  if (code.value.length !== 6) {
    resetErr.value = t.value.errors.codeInvalid
    return
  }
  if (newPassword.value.length < 6) {
    resetErr.value = t.value.auth.passwordTooShort
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    resetErr.value = t.value.errors.pwMismatch
    return
  }
  resetting.value = true
  resetErr.value = ''
  try {
    await authApi.resetPassword(email.value.trim().toLowerCase(), code.value, newPassword.value)
    resetOk.value = true
    setTimeout(() => router.push('/login'), 2000)
  } catch (e: any) {
    resetErr.value = e.response?.data?.detail || '重置失败'
  } finally {
    resetting.value = false
  }
}

async function resendCode() {
  if (cooldown.value > 0) return
  try {
    await authApi.forgotPassword(email.value.trim().toLowerCase())
    startCooldown()
    resetErr.value = ''
  } catch (e: any) {
    resetErr.value = e.response?.data?.detail || '发送失败'
  }
}
</script>

<template>
  <AuthLayout>
    <!-- Step 1: Email -->
    <template v-if="step === 'email'" #title>{{ t.auth.resetPasswordTitle }}</template>
    <template v-if="step === 'email'" #subtitle>{{ t.auth.resetPasswordSubtitle }}</template>

    <template v-if="step === 'email'">
      <form class="auth-form" @submit.prevent="doSendCode()">
        <label>{{ t.auth.email }}</label>
        <input v-model="email" type="email" :placeholder="t.auth.emailPlaceholder" />
        <button class="btn btn-primary auth-btn" type="submit" :disabled="sending || !email.trim()">
          {{ sending ? t.auth.registering : t.auth.resetPasswordBtn }}
        </button>
        <p v-if="sentErr" class="auth-err">{{ sentErr }}</p>
      </form>
      <p class="auth-switch">
        <router-link to="/login">{{ t.auth.back }}</router-link>
      </p>
    </template>

    <!-- Step 2: Reset -->
    <template v-if="step === 'reset'" #title>{{ t.auth.resetPasswordTitle }}</template>
    <template v-if="step === 'reset'" #subtitle>{{ _('auth.verifyEmailSubtitle', { email: email.trim().toLowerCase() }) }}</template>

    <template v-if="step === 'reset'">
      <div class="auth-form">
        <label>{{ t.auth.verifyCode }}</label>
        <input
          v-model="code"
          type="text"
          inputmode="numeric"
          maxlength="6"
          :placeholder="t.auth.verifyCodePlaceholder"
          class="code-input"
          @input="code = code.replace(/\D/g, '').slice(0, 6)"
          @keyup.enter="doReset"
        />

        <label>{{ t.auth.newPassword }}</label>
        <input v-model="newPassword" type="password" :placeholder="t.auth.newPasswordPlaceholder" />

        <label>{{ t.auth.confirmPassword }}</label>
        <input v-model="confirmPassword" type="password" :placeholder="t.auth.confirmPasswordPlaceholder" />

        <button class="btn btn-primary auth-btn" :disabled="resetting || code.length !== 6 || !newPassword || !confirmPassword" @click="doReset">
          {{ resetting ? t.auth.resetting : t.auth.resetPasswordBtn }}
        </button>

        <button class="btn btn-ghost resend-btn" :disabled="cooldown > 0" @click="resendCode">
          {{ cooldown > 0 ? _('auth.resendIn', { n: cooldown }) : t.auth.resendCode }}
        </button>

        <p v-if="resetErr" class="auth-err">{{ resetErr }}</p>
        <p v-if="resetOk" class="auth-ok">{{ t.auth.resetSuccess }}</p>
      </div>
    </template>
  </AuthLayout>
</template>

<style scoped>
/* ---- Form layout ---- */
.auth-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.auth-form input {
  width: 100%;
  font-size: 14px;
  padding: 10px 14px;
  background: var(--c-bg-input);
  border: 1px solid var(--c-border);
  border-radius: var(--radius-sm);
  color: var(--c-text);
  font-family: inherit;
  outline: none;
  box-sizing: border-box;
}
.auth-form input:focus { border-color: var(--c-accent); }
.auth-form input::placeholder { color: var(--c-text-muted); }

.auth-btn {
  width: 100%;
  padding: 10px;
  justify-content: center;
  margin-top: 6px;
}

.auth-err {
  font-size: 12px;
  color: var(--c-danger);
  text-align: center;
}

.auth-ok {
  font-size: 12px;
  color: var(--c-accent);
  text-align: center;
}

.auth-switch {
  margin-top: 20px;
  text-align: center;
  font-size: 13px;
  color: var(--c-text-muted);
}
.auth-switch a { color: var(--c-accent); text-decoration: none; }

/* ---- Specific to this page ---- */
.code-input {
  font-size: 28px !important;
  padding: 12px 16px !important;
  text-align: center;
  letter-spacing: 12px;
  font-family: var(--font-mono);
}
.resend-btn {
  width: 100%;
  margin-top: 4px;
  font-size: 13px;
  justify-content: center;
}
</style>
