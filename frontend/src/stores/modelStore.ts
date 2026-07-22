/** 模型管理 Store —— 含音色配对 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ModelInfo, ModelListResponse, VoiceProfile } from '../types'
import { modelApi, profileApi } from '../api'

export const useModelStore = defineStore('model', () => {
  const t2sModels = ref<ModelInfo[]>([])
  const vitsModels = ref<ModelInfo[]>([])
  const selectedT2s = ref<string>('')
  const selectedVits = ref<string>('')
  const isLoaded = ref(false)
  const isLoading = ref(false)
  const loadError = ref<string | null>(null)

  // 音色配对
  const profiles = ref<VoiceProfile[]>([])
  const selectedProfileId = ref<string>('')

  async function refreshList() {
    try {
      const [modelRes, profileRes] = await Promise.all([
        modelApi.list(),
        profileApi.list(),
      ])
      const data = modelRes.data as ModelListResponse
      t2sModels.value = data.t2s_models
      vitsModels.value = data.vits_models
      isLoaded.value = data.status.is_loaded
      if (data.status.current_t2s) selectedT2s.value = data.status.current_t2s
      if (data.status.current_vits) selectedVits.value = data.status.current_vits
      profiles.value = (profileRes.data as VoiceProfile[]) || []
    } catch (e: any) {
      console.error('获取模型列表失败:', e)
    }
  }

  async function uploadModel(file: File): Promise<string | false> {
    try {
      const res = await modelApi.upload(file)
      const info = res.data as ModelInfo
      await refreshList()
      return info.filename
    } catch (e: any) {
      loadError.value = e.response?.data?.detail || '上传失败'
      return false
    }
  }

  async function createProfile(
    name: string, description: string,
    t2sPath: string, vitsPath: string,
    image?: string | null,
  ) {
    await profileApi.create(name, description, t2sPath, vitsPath, image)
    await refreshList()
  }

  async function updateProfile(
    id: string,
    data: { name?: string; description?: string; image?: string | null },
  ) {
    await profileApi.update(id, data)
    await refreshList()
  }

  async function deleteProfile(id: string) {
    await profileApi.delete(id)
    await refreshList()
  }

  function selectProfile(profileId: string) {
    const p = profiles.value.find(p => p.id === profileId)
    if (p) {
      selectedProfileId.value = p.id
      selectedT2s.value = p.t2s_file
      selectedVits.value = p.vits_file
    }
  }

  async function loadSelected() {
    if (!selectedT2s.value || !selectedVits.value) {
      loadError.value = '请先选择模型或音色'
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
    profiles, selectedProfileId,
    refreshList, uploadModel, createProfile, updateProfile, deleteProfile,
    selectProfile, loadSelected,
  }
})
