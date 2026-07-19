/** TTS Store —— 参数 + 合成状态 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { SplitMethod } from '../types'
import { ttsApi } from '../api'

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
      })

      audioBlob.value = res.data
      if (audioUrl.value) URL.revokeObjectURL(audioUrl.value)
      audioUrl.value = URL.createObjectURL(res.data)

      const taskIdHeader = res.headers['x-task-id']
      if (taskIdHeader) taskId.value = taskIdHeader

      taskState.value = 'done'
    } catch (e: any) {
      taskState.value = 'error'
      taskError.value = e.response?.data?.detail || e.message || '推理失败'
    }
  }

  async function cancelTask() {
    if (!taskId.value) return
    try {
      await ttsApi.cancel(taskId.value)
      taskState.value = 'idle'
    } catch (e: any) {
      console.error('取消失败:', e)
    }
  }

  return {
    text, refAudioPath, refAudioFileName, promptText,
    speedFactor, splitMethod, topK, topP, temperature, seed,
    showAdvanced,
    taskId, taskState, taskError, audioBlob, audioUrl,
    charCount, maxChars,
    updateCharCount, uploadRefAudio, startSynthesis, cancelTask,
  }
})
