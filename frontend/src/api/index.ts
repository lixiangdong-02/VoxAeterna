/** axios 封装 —— 统一请求后端 API */

import axios from 'axios'

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
    return api.get('/tts/history')
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
