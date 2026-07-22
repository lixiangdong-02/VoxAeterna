<script setup lang="ts">
import { ref, computed, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'
import { useLocaleStore } from '@/stores/localeStore'
import { authApi } from '@/api'
import AuthLayout from '@/components/AuthLayout.vue'

const router = useRouter()
const authStore = useAuthStore()
const localeStore = useLocaleStore()
const t = computed(() => localeStore.t)
const _ = localeStore._

// Step: 'form' | 'verify'
const step = ref<'form' | 'verify'>('form')

// Form fields
const email = ref('')
const username = ref('')
const password = ref('')
const isLoading = ref(false)
const formError = ref('')

// Email validation
const emailError = ref('')
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
function validateEmail() {
  if (!email.value.trim()) { emailError.value = ''; return }
  if (!EMAIL_RE.test(email.value.trim())) {
    emailError.value = t.value.auth.emailFormatError
  } else {
    emailError.value = ''
  }
}

// Password validation
const passwordError = ref('')
function validatePassword() {
  if (!password.value) { passwordError.value = ''; return }
  if (password.value.length < 6) {
    passwordError.value = t.value.auth.passwordTooShort
  } else {
    passwordError.value = ''
  }
}

// Username validation
const usernameError = ref('')
function validateUsername() {
  if (!username.value.trim()) { usernameError.value = ''; return }
  if (username.value.trim().length < 2) {
    usernameError.value = t.value.auth.usernameRequired
  } else {
    usernameError.value = ''
  }
}

async function doRegister() {
  // Validate all fields
  validateEmail()
  validatePassword()
  validateUsername()
  if (emailError.value || passwordError.value || usernameError.value) return
  if (!email.value.trim() || !username.value.trim() || !password.value) return

  isLoading.value = true
  formError.value = ''
  try {
    await authApi.register(email.value.trim().toLowerCase(), username.value.trim(), password.value)
    // Send verification code
    await authApi.sendVerifyCode(email.value.trim().toLowerCase(), 'register')
    step.value = 'verify'
  } catch (e: any) {
    formError.value = e.response?.data?.detail || t.value.auth.registerFailed
  } finally {
    isLoading.value = false
  }
}

// Verify step
const verifyCode = ref('')
const verifying = ref(false)
const verifyError = ref('')
const verifySuccess = ref(false)
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

// Start cooldown when entering verify step
watch(step, (val) => {
  if (val === 'verify') startCooldown()
})

onUnmounted(() => clearCooldown())

async function doVerify() {
  if (verifyCode.value.length !== 6) {
    verifyError.value = t.value.errors.codeInvalid
    return
  }
  verifying.value = true
  verifyError.value = ''
  try {
    await authApi.verifyEmail(email.value.trim().toLowerCase(), verifyCode.value)
    verifySuccess.value = true
    // Auto-login after verification
    const result = await authStore.login(email.value.trim().toLowerCase(), password.value)
    if (result.ok) {
      router.push('/workspace')
    } else {
      // If still can't login, redirect to login page
      router.push('/login')
    }
  } catch (e: any) {
    verifyError.value = e.response?.data?.detail || t.value.auth.registerFailed
  } finally {
    verifying.value = false
  }
}

async function resendCode() {
  if (cooldown.value > 0) return
  try {
    await authApi.sendVerifyCode(email.value.trim().toLowerCase(), 'register')
    startCooldown()
    verifyError.value = ''
  } catch (e: any) {
    verifyError.value = e.response?.data?.detail || '发送失败'
  }
}
</script>

<template>
  <AuthLayout>
    <!-- Step 1: Registration Form -->
    <template v-if="step === 'form'" #title>{{ t.auth.registerTitle }}</template>
    <template v-if="step === 'form'" #subtitle>{{ t.auth.registerSubtitle }}</template>

    <template v-if="step === 'form'">
      <form class="auth-form" @submit.prevent="doRegister()">
        <label>{{ t.auth.email }}</label>
        <input
          v-model="email"
          type="email"
          :placeholder="t.auth.emailPlaceholder"
          @blur="validateEmail"
          @input="emailError = ''"
        />
        <p v-if="emailError" class="field-err">{{ emailError }}</p>

        <label>{{ t.auth.username }}</label>
        <input
          v-model="username"
          type="text"
          :placeholder="t.auth.usernamePlaceholder"
          @blur="validateUsername"
          @input="usernameError = ''"
        />
        <p v-if="usernameError" class="field-err">{{ usernameError }}</p>

        <label>{{ t.auth.password }}</label>
        <input
          v-model="password"
          type="password"
          :placeholder="t.auth.passwordPlaceholder"
          @blur="validatePassword"
          @input="passwordError = ''"
        />
        <p v-if="passwordError" class="field-err">{{ passwordError }}</p>

        <button class="btn btn-primary auth-btn" type="submit" :disabled="isLoading">
          {{ isLoading ? t.auth.registering : t.auth.registerBtn }}
        </button>

        <p v-if="formError" class="auth-err">{{ formError }}</p>
      </form>

      <p class="auth-switch">
        {{ t.auth.hasAccount }}<router-link to="/login">{{ t.hero.login }}</router-link>
      </p>
    </template>

    <!-- Step 2: Email Verification -->
    <template v-if="step === 'verify'" #title>{{ t.auth.verifyEmailTitle }}</template>
    <template v-if="step === 'verify'" #subtitle>{{ _('auth.verifyEmailSubtitle', { email: email.trim().toLowerCase() }) }}</template>

    <template v-if="step === 'verify'">
      <div class="auth-form">
        <label>{{ t.auth.verifyCode }}</label>
        <div class="code-input-wrap">
          <input
            v-model="verifyCode"
            type="text"
            inputmode="numeric"
            maxlength="6"
            :placeholder="t.auth.verifyCodePlaceholder"
            class="code-input"
            @input="verifyCode = verifyCode.replace(/\D/g, '').slice(0, 6)"
            @keyup.enter="doVerify"
          />
        </div>
        <p v-if="verifyError" class="auth-err">{{ verifyError }}</p>
        <p v-if="verifySuccess" class="auth-ok">{{ t.auth.verifySuccess }}</p>

        <button class="btn btn-primary auth-btn" :disabled="verifying || verifyCode.length !== 6" @click="doVerify">
          {{ verifying ? t.auth.verifying : t.auth.verifyBtn }}
        </button>

        <button class="btn btn-ghost resend-btn" :disabled="cooldown > 0" @click="resendCode">
          {{ cooldown > 0 ? _('auth.resendIn', { n: cooldown }) : t.auth.resendCode }}
        </button>
      </div>
    </template>
  </AuthLayout>
</template>

<style scoped>
/* ---- Form layout (same as LoginPage) ---- */
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

.auth-switch {
  margin-top: 20px;
  text-align: center;
  font-size: 13px;
  color: var(--c-text-muted);
}
.auth-switch a { color: var(--c-accent); text-decoration: none; }
.auth-switch a:hover { text-decoration: underline; }

/* ---- Specific to this page ---- */
.field-err {
  font-size: 11px;
  color: var(--c-danger);
  margin: -6px 0 0 0;
}
.auth-ok {
  font-size: 12px;
  color: var(--c-accent);
  text-align: center;
}
.code-input-wrap {
  margin-bottom: 4px;
}
.code-input {
  width: 100% !important;
  font-size: 28px !important;
  padding: 12px 16px !important;
  text-align: center;
  letter-spacing: 12px;
  font-family: var(--font-mono);
}
.resend-btn {
  width: 100%;
  margin-top: 8px;
  font-size: 13px;
  justify-content: center;
}
</style>
