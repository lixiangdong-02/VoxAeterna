<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'
import { useLocaleStore } from '@/stores/localeStore'
import { authApi } from '@/api'
import AuthLayout from '@/components/AuthLayout.vue'

const router = useRouter()
const authStore = useAuthStore()
const localeStore = useLocaleStore()
const t = computed(() => localeStore.t)

const email = ref('')
const password = ref('')
const isLoading = ref(false)

async function doLogin() {
  isLoading.value = true
  const result = await authStore.login(email.value, password.value)
  isLoading.value = false
  if (result.ok) {
    router.push('/workspace')
  } else if (result.needVerify) {
    // Redirect to verification: store email in session so register page can pick it up
    router.push({ path: '/register', query: { verify: email.value } })
  }
}
</script>

<template>
  <AuthLayout>
    <template #title>{{ t.auth.loginTitle }}</template>
    <template #subtitle>{{ t.auth.loginSubtitle }}</template>

    <form class="auth-form" @submit.prevent="doLogin()">
      <label>{{ t.auth.email }}</label>
      <input v-model="email" type="email" :placeholder="t.auth.emailPlaceholder" />

      <label>{{ t.auth.password }}</label>
      <input v-model="password" type="password" :placeholder="t.auth.passwordPlaceholder" />

      <div class="forgot-wrap">
        <router-link to="/forgot-password" class="forgot-link">{{ t.auth.forgotPassword }}</router-link>
      </div>

      <button class="btn btn-primary auth-btn" type="submit" :disabled="isLoading">
        {{ isLoading ? t.auth.loggingIn : t.auth.loginBtn }}
      </button>

      <p v-if="authStore.loginError" class="auth-err">
        {{ authStore.loginError }}
        <span v-if="authStore.loginError.includes('验证邮箱')">
          — <router-link to="/register" class="inline-link">{{ t.auth.resendVerifyCode }}</router-link>
        </span>
      </p>
    </form>

    <p class="auth-switch">
      {{ t.auth.noAccount }}<router-link to="/register">{{ t.hero.register }}</router-link>
    </p>
  </AuthLayout>
</template>

<style scoped>
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

.auth-btn { width: 100%; padding: 10px; justify-content: center; margin-top: 6px; }
.auth-err { font-size: 12px; color: var(--c-danger); text-align: center; }
.auth-switch {
  margin-top: 20px;
  text-align: center;
  font-size: 13px;
  color: var(--c-text-muted);
}
.auth-switch a { color: var(--c-accent); text-decoration: none; }
.auth-switch a:hover { text-decoration: underline; }
.forgot-wrap {
  text-align: right;
  margin-top: -4px;
}
.forgot-link {
  font-size: 12px;
  color: var(--c-text-muted);
  text-decoration: none;
}
.forgot-link:hover { color: var(--c-accent); text-decoration: underline; }
.inline-link { color: var(--c-accent); }
</style>
