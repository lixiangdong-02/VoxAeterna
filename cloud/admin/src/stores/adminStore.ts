import { defineStore } from 'pinia'
import { ref } from 'vue'
import { admin } from '../api'

export const useAdminStore = defineStore('admin', () => {
  const token = ref(localStorage.getItem('admin_token') || '')
  const isLoggedIn = ref(!!token.value)
  const loginError = ref('')

  // 仪表盘数据
  const stats = ref({ total_users: 0, active_subscriptions: 0, total_synthesis_count: 0, pending_orders: 0 })
  const users = ref<any[]>([])
  const usersTotal = ref(0)
  const usersPage = ref(1)
  const searchQuery = ref('')

  const announcements = ref<any[]>([])

  async function login(email: string, password: string) {
    loginError.value = ''
    try {
      const res = await admin.login(email, password)
      const t = res.data.access_token
      token.value = t
      isLoggedIn.value = true
      localStorage.setItem('admin_token', t)
      return true
    } catch (e: any) {
      loginError.value = e.response?.data?.detail || '登录失败'
      return false
    }
  }

  function logout() {
    token.value = ''
    isLoggedIn.value = false
    localStorage.removeItem('admin_token')
  }

  async function fetchStats() {
    const res = await admin.stats()
    stats.value = res.data
  }

  async function fetchUsers(page = 1, search = '') {
    usersPage.value = page
    searchQuery.value = search
    const res = await admin.users(page, search)
    users.value = res.data.items
    usersTotal.value = res.data.total
  }

  async function updateUser(userId: number, data: any) {
    await admin.updateUser(userId, data)
    await fetchUsers(usersPage.value, searchQuery.value)
  }

  async function createSubscription(data: { user_id: number; plan: string; duration_days?: number }) {
    await admin.createSubscription(data)
    await fetchUsers(usersPage.value, searchQuery.value)
  }

  async function fetchAnnouncements() {
    const res = await admin.announcements()
    announcements.value = res.data
  }

  async function createAnnouncement(data: { title: string; body: string }) {
    await admin.createAnnouncement(data)
    await fetchAnnouncements()
  }

  async function updateAnnouncement(id: number, data: any) {
    await admin.updateAnnouncement(id, data)
    await fetchAnnouncements()
  }

  return {
    token, isLoggedIn, loginError,
    stats, users, usersTotal, usersPage, searchQuery,
    announcements,
    login, logout,
    fetchStats, fetchUsers, updateUser, createSubscription,
    fetchAnnouncements, createAnnouncement, updateAnnouncement,
  }
})
