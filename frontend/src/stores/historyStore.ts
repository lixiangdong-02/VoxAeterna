/** 历史记录 Store —— 最近 5 条 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { HistoryRecord, ExportFormat } from '../types'
import { ttsApi, exportApi } from '../api'

export const useHistoryStore = defineStore('history', () => {
  const records = ref<HistoryRecord[]>([])

  async function refresh() {
    try {
      const res = await ttsApi.history()
      records.value = (res.data as HistoryRecord[]) || []
    } catch (e) {
      console.error('获取历史失败:', e)
    }
  }

  async function exportAudio(taskId: string, format: ExportFormat) {
    try {
      const res = await exportApi.download(taskId, format)
      const blob = res.data as Blob
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${taskId}.${format}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error('导出失败:', e)
    }
  }

  return { records, refresh, exportAudio }
})
