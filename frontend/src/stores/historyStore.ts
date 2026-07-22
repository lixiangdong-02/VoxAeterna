/** 历史记录 Store —— 按用户从 SQLite 查询 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { HistoryRecord, ExportFormat } from '../types'
import { ttsApi, exportApi } from '../api'

export const useHistoryStore = defineStore('history', () => {
  const records = ref<HistoryRecord[]>([])

  async function refresh(userId: number = 0) {
    try {
      if (userId > 0) {
        const res = await ttsApi.historyByUser(userId)
        records.value = (res.data as HistoryRecord[]) || []
      } else {
        // 兼容：无 user_id 时不尝试
        records.value = []
      }
    } catch (e) {
      console.error('获取历史失败:', e)
    }
  }

  async function deleteRecord(taskId: string, userId: number) {
    try {
      await ttsApi.deleteHistory(taskId, userId)
      await refresh(userId)
    } catch (e) {
      console.error('删除失败:', e)
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

  return { records, refresh, deleteRecord, exportAudio }
})
