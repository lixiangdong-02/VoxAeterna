/** 管理后台 API 封装 */
import axios from 'axios'

const adminApi = axios.create({
  baseURL: 'http://127.0.0.1:8000/api/v1',
  timeout: 30000,
})

// 请求拦截器 —— 自动带 token
adminApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器 —— 401 跳转登录
adminApi.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('admin_token')
      window.location.hash = '/login'
    }
    return Promise.reject(err)
  }
)

export const admin = {
  login(email: string, password: string) {
    return adminApi.post('/auth/login', { email, password })
  },
  stats() {
    return adminApi.get('/admin/stats')
  },
  users(page = 1, search = '') {
    return adminApi.get('/admin/users', { params: { page, search } })
  },
  updateUser(userId: number, data: { status?: string; role?: string }) {
    return adminApi.put(`/admin/users/${userId}`, data)
  },
  createSubscription(data: { user_id: number; plan: string; duration_days?: number }) {
    return adminApi.post('/admin/subscriptions', data)
  },
  announcements() {
    return adminApi.get('/announcements')
  },
  createAnnouncement(data: { title: string; body: string }) {
    return adminApi.post('/admin/announcements', data)
  },
  updateAnnouncement(id: number, data: { title?: string; body?: string; is_active?: boolean }) {
    return adminApi.put(`/admin/announcements/${id}`, data)
  },
}
