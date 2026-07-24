/** axios 封装 —— 统一请求后端 API */

import axios from 'axios'
import { getDeviceFingerprint } from '@/utils/fingerprint'

const BASE = 'http://127.0.0.1:9880/api'
const api = axios.create({
  baseURL: BASE,
  timeout: 120000,  // 模型加载可能很慢
})

// ======================= 模型管理 =======================

export const modelApi = {
  list() {
    return api.get('/models/list')
  },
  upload(file: File) {
    const form = new FormData()
    form.append('file', file)
    return api.post('/models/upload', form)
  },
  load(t2s_path: string, vits_path: string) {
    return api.post('/models/load', { t2s_path, vits_path })
  },
  status() {
    return api.get('/models/status')
  },
}

export const profileApi = {
  list() {
    return api.get('/profiles')
  },
  create(name: string, description: string, t2sPath: string, vitsPath: string, image?: string | null) {
    return api.post('/profiles', { name, description, t2s_path: t2sPath, vits_path: vitsPath, image: image || null })
  },
  update(id: string, data: { name?: string; description?: string; image?: string | null }) {
    return api.put(`/profiles/${id}`, data)
  },
  delete(id: string) {
    return api.delete(`/profiles/${id}`)
  },
  uploadImage(file: File) {
    const form = new FormData()
    form.append('file', file)
    return api.post('/profiles/image', form)
  },
}

// ======================= 参考音频 =======================

export const audioApi = {
  uploadRef(file: File) {
    const form = new FormData()
    form.append('file', file)
    return api.post('/audio/upload-ref', form)
  },
}

// ======================= TTS =======================

export const ttsApi = {
  synthesize(data: {
    text: string
    text_lang: string
    ref_audio_path: string
    prompt_text: string
    prompt_lang: string
    speed_factor: number
    text_split_method: string
    top_k: number
    top_p: number
    temperature: number
    batch_size: number
    seed: number
    streaming: boolean
    user_id?: number
  }) {
    return api.post('/tts/synthesize', data, {
      responseType: 'blob',
    })
  },
  cancel(taskId: string) {
    return api.post('/tts/cancel', null, { params: { task_id: taskId } })
  },
  getStatus(taskId: string) {
    return api.get('/tts/status', { params: { task_id: taskId } })
  },
  history() {
    return api.get('/tts/history', { params: { user_id: 0 } })
  },
  historyByUser(userId: number) {
    return api.get('/tts/history', { params: { user_id: userId } })
  },
  deleteHistory(taskId: string, userId: number) {
    return api.delete(`/tts/history/${taskId}`, { params: { user_id: userId } })
  },
}

// ======================= 导出 =======================

export const exportApi = {
  download(taskId: string, format: 'wav' | 'mp3') {
    return api.get(`/audio/export/${taskId}`, {
      params: { format },
      responseType: 'blob',
    })
  },
}

// ======================= 云端 API（端口 8000）=========================

const cloudAxios = axios.create({
  baseURL: 'https://voxaeterna-jlekcxjcva.cn-hangzhou.fcapp.run/api/v1',
  timeout: 30000,
})

// 自动挂 token
cloudAxios.interceptors.request.use((config) => {
  const token = localStorage.getItem('vox_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const authApi = {
  register(email: string, username: string, password: string) {
    return cloudAxios.post('/auth/register', { email, username, password })
  },
  async login(email: string, password: string) {
    const fp = await getDeviceFingerprint()
    return cloudAxios.post('/auth/login', { email, password, device_fingerprint: fp })
  },
  profile(token: string) {
    return cloudAxios.get('/auth/profile', { headers: { Authorization: `Bearer ${token}` } })
  },
  updateProfile(username: string) {
    return cloudAxios.put('/auth/profile', { username })
  },
  changePassword(oldPassword: string, newPassword: string) {
    return cloudAxios.put('/auth/password', { old_password: oldPassword, new_password: newPassword })
  },
  async refresh() {
    const fp = await getDeviceFingerprint()
    return cloudAxios.post('/auth/refresh', { device_fingerprint: fp })
  },
  sendVerifyCode(email: string, purpose: string = 'register') {
    return cloudAxios.post('/auth/send-verify-code', { email, purpose })
  },
  verifyEmail(email: string, code: string) {
    return cloudAxios.post('/auth/verify-email', { email, code })
  },
  forgotPassword(email: string) {
    return cloudAxios.post('/auth/forgot-password', { email, purpose: 'reset_password' })
  },
  resetPassword(email: string, code: string, newPassword: string) {
    return cloudAxios.post('/auth/reset-password', { email, code, new_password: newPassword })
  },
  logout() {
    return cloudAxios.post('/auth/logout')
  },
}


export const versionApi = {
  async check() {
    return cloudAxios.get('/version/latest')
  },
}
export const cloudApi = {
  subscriptionStatus() {
    return cloudAxios.get('/subscription/status')
  },
  createOrder(plan: string) {
    return cloudAxios.post('/subscription/order', { plan })
  },
  getOrderStatus(orderId: number) {
    return cloudAxios.get(`/subscription/order/${orderId}`)
  },
  getPaymentHistory(page: number = 1) {
    return cloudAxios.get('/subscription/payment-history', { params: { page } })
  },
  getUsageStats() {
    return cloudAxios.get('/user/usage-stats')
  },
  listSessions() {
    return cloudAxios.get('/user/sessions')
  },
  revokeAllSessions() {
    return cloudAxios.post('/user/sessions/revoke-all')
  },
  deleteAccount(password: string) {
    return cloudAxios.delete('/user/account', { data: { password } })
  },
  async trialStatus() {
    const fp = await getDeviceFingerprint()
    return cloudAxios.get('/trial/status', { params: { device_fingerprint: fp } })
  },
  async syncTrial(remaining: number) {
    const fp = await getDeviceFingerprint()
    return cloudAxios.post('/trial/sync', { device_fingerprint: fp, remaining })
  },
  async consumeTrial() {
    const fp = await getDeviceFingerprint()
    return cloudAxios.post('/trial/consume', { device_fingerprint: fp })
  },
  async reportUsage(textLength: number, duration: number) {
    const fp = await getDeviceFingerprint()
    return cloudAxios.post('/usage/report', { text_length: textLength, duration_seconds: duration, device: fp })
  },
  announcements() {
    return cloudAxios.get('/announcements')
  },
}
