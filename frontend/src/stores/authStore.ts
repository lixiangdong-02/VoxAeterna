import type { UserInfo } from '@/types'
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('vox_token') || '')
  const isLoggedIn = ref(!!token.value)
  const user = ref<UserInfo | null>(null)
  const loginError = ref('')
  const registerError = ref('')

  async function restoreSession() {
    if (!token.value) return false
    try {
      const res = await authApi.profile(token.value)
      user.value = res.data
      isLoggedIn.value = true
      return true
    } catch {
      logout()
      return false
    }
  }

  async function login(email: string, password: string) {
    loginError.value = ''
    try {
      const res = await authApi.login(email, password)
      const data = res.data
      if (data.error === 'email_not_verified') {
        loginError.value = data.message || '请先验证邮箱'
        return { ok: false, needVerify: true }
      }
      token.value = data.access_token
      user.value = data.user
      isLoggedIn.value = true
      localStorage.setItem('vox_token', token.value)
      localStorage.setItem('vox_user_id', String(data.user.id))
      return { ok: true }
    } catch (e: any) {
      const detail = e.response?.data?.detail || '登录失败'
      const status = e.response?.status
      if (status === 403) {
        loginError.value = detail
        return { ok: false, needVerify: true }
      }
      loginError.value = detail
      return { ok: false }
    }
  }

  async function register(email: string, username: string, password: string) {
    registerError.value = ''
    try {
      await authApi.register(email, username, password)
      return true
    } catch (e: any) {
      registerError.value = e.response?.data?.detail || '注册失败'
      return false
    }
  }

  async function logout() {
    try { await authApi.logout() } catch { /* ignore */ }
    token.value = ''
    user.value = null
    isLoggedIn.value = false
    localStorage.removeItem('vox_token')
    localStorage.removeItem('vox_user_id')
  }

  return { token, isLoggedIn, user, loginError, registerError, restoreSession, login, register, logout }
})
