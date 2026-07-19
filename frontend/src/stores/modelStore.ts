/** 模型管理 Store */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ModelInfo, ModelListResponse } from '../types'
import { modelApi } from '../api'

export const useModelStore = defineStore('model', () => {
  const t2sModels = ref<ModelInfo[]>([])
  const vitsModels = ref<ModelInfo[]>([])
  const selectedT2s = ref<string>('')
  const selectedVits = ref<string>('')
  const isLoaded = ref(false)
  const isLoading = ref(false)
  const loadError = ref<string | null>(null)

  async function refreshList() {
    try {
      const res = await modelApi.list()
      const data = res.data as ModelListResponse
      t2sModels.value = data.t2s_models
      vitsModels.value = data.vits_models
      isLoaded.value = data.status.is_loaded
      if (data.status.current_t2s) selectedT2s.value = data.status.current_t2s
      if (data.status.current_vits) selectedVits.value = data.status.current_vits
    } catch (e: any) {
      console.error('获取模型列表失败:', e)
    }
  }

  async function uploadModel(file: File) {
    try {
      await modelApi.upload(file)
      await refreshList()
      return true
    } catch (e: any) {
      loadError.value = e.response?.data?.detail || '上传失败'
      return false
    }
  }

  async function loadSelected() {
    if (!selectedT2s.value || !selectedVits.value) {
      loadError.value = '请先选择两个模型文件'
      return false
    }
    isLoading.value = true
    loadError.value = null
    try {
      await modelApi.load(selectedT2s.value, selectedVits.value)
      isLoaded.value = true
      return true
    } catch (e: any) {
      loadError.value = e.response?.data?.detail || '加载失败'
      return false
    } finally {
      isLoading.value = false
    }
  }

  return {
    t2sModels, vitsModels, selectedT2s, selectedVits,
    isLoaded, isLoading, loadError,
    refreshList, uploadModel, loadSelected,
  }
})
