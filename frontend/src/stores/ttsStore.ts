/** TTS Store —— 参数 + 合成状态 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { SplitMethod } from '../types'
import { ttsApi } from '../api'
import { useAuthStore } from './authStore'

/** 从 blob 解码音频时长（秒） */
function getAudioDuration(blob: Blob): Promise<number> {
  return new Promise((resolve) => {
    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)()
    const reader = new FileReader()
    reader.onload = () => {
      ctx.decodeAudioData(reader.result as ArrayBuffer, (buffer) => {
        resolve(buffer.duration)
        ctx.close()
      }, () => { resolve(0); ctx.close() })
    }
    reader.onerror = () => resolve(0)
    reader.readAsArrayBuffer(blob)
  })
}

export const useTtsStore = defineStore('tts', () => {
  const text = ref('')
  const refAudioPath = ref('')
  const refAudioFileName = ref('')
  const promptText = ref('')
  const speedFactor = ref(1.0)
  const splitMethod = ref<SplitMethod>('cut5')
  const topK = ref(5)
  const topP = ref(1.0)
  const temperature = ref(1.0)
  const seed = ref(-1)
  const showAdvanced = ref(false)

  const taskId = ref<string | null>(null)
  const taskState = ref<'idle' | 'running' | 'done' | 'error'>('idle')
  const taskError = ref<string | null>(null)
  const audioBlob = ref<Blob | null>(null)
  const audioUrl = ref<string | null>(null)

  const charCount = ref(0)
  const maxChars = 500

  function updateCharCount(t: string) {
    charCount.value = t.length
  }

  async function uploadRefAudio(file: File) {
    const { audioApi } = await import('../api')
    const res = await audioApi.uploadRef(file)
    refAudioPath.value = res.data.filename
    refAudioFileName.value = file.name
  }

  async function startSynthesis() {
    if (!text.value.trim()) return
    taskState.value = 'running'
    taskError.value = null

    // 获取当前用户 ID（从 authStore，而非 localStorage）
    const userId = useAuthStore().user?.id || 0

    try {
      const res = await ttsApi.synthesize({
        text: text.value,
        text_lang: 'zh',
        ref_audio_path: refAudioPath.value,
        prompt_text: promptText.value || ' ',
        prompt_lang: 'zh',
        speed_factor: speedFactor.value,
        text_split_method: splitMethod.value,
        top_k: topK.value,
        top_p: topP.value,
        temperature: temperature.value,
        batch_size: 1,
        seed: seed.value,
        streaming: false,
        user_id: userId,
      })

      audioBlob.value = res.data
      if (audioUrl.value) URL.revokeObjectURL(audioUrl.value)
      audioUrl.value = URL.createObjectURL(res.data)

      const taskIdHeader = res.headers['x-task-id']
      if (taskIdHeader) taskId.value = taskIdHeader

      taskState.value = 'done'

      // 自动存入保存区
      try {
        const { useClipStore } = await import('./clipStore')
        const clipStore = useClipStore()
        const headerDur = Number(res.headers['x-audio-duration'])
        const duration = headerDur > 0 ? headerDur : await getAudioDuration(res.data)
        const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
        clipStore.addClip(`合成-${ts}`, res.data, duration)
        console.log('[ttsStore] 已自动保存到保存区, 时长:', duration)
      } catch (e: any) {
        console.warn('[ttsStore] 自动保存失败:', e)
      }
    } catch (e: any) {
      taskState.value = 'error'
      taskError.value = e.response?.data?.detail || e.message || '推理失败'
    }
  }

  async function cancelTask() {
    if (!taskId.value) return
    const userId = useAuthStore().user?.id || 0
    try {
      await ttsApi.cancel(taskId.value)
      taskState.value = 'idle'
    } catch (e: any) {
      console.error('取消失败:', e)
    }
  }

  function loadFromHistory(record: {
    text?: string | null
    prompt_text?: string | null
    speed_factor?: number | null
    ref_audio_path?: string | null
  }) {
    text.value = record.text || ''
    promptText.value = record.prompt_text || ''
    if (record.speed_factor != null) speedFactor.value = record.speed_factor
    if (record.ref_audio_path) refAudioPath.value = record.ref_audio_path
    updateCharCount(text.value)
  }

  return {
    text, refAudioPath, refAudioFileName, promptText,
    speedFactor, splitMethod, topK, topP, temperature, seed,
    showAdvanced,
    taskId, taskState, taskError, audioBlob, audioUrl,
    charCount, maxChars,
    updateCharCount, uploadRefAudio, startSynthesis, cancelTask,
    loadFromHistory,
  }
})
