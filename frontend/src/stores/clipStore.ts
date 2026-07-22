/** 保存区 & 编辑轨道 Store */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { SavedClip, EditorTrack } from '../types'

function uid(): string {
  return crypto.randomUUID().slice(0, 8)
}

export const useClipStore = defineStore('clip', () => {
  // ===== 保存区 =====
  const savedClips = ref<SavedClip[]>([])

  function addClip(name: string, blob: Blob, duration: number) {
    const url = URL.createObjectURL(blob)
    savedClips.value.push({
      id: uid(),
      name,
      blob,
      url,
      duration,
      createdAt: new Date().toISOString(),
    })
  }

  function removeClip(id: string) {
    const idx = savedClips.value.findIndex(c => c.id === id)
    if (idx !== -1) {
      URL.revokeObjectURL(savedClips.value[idx].url)
      savedClips.value.splice(idx, 1)
    }
  }

  // ===== 编辑区轨道 =====
  const tracks = ref<EditorTrack[]>([])

  function addTrack(clip: SavedClip) {
    tracks.value.push({
      id: uid(),
      clipId: clip.id,
      name: clip.name,
      url: clip.url,
      duration: clip.duration,
      startOffset: 0,
      endOffset: clip.duration,
    })
  }

  function removeTrack(trackId: string) {
    tracks.value = tracks.value.filter(t => t.id !== trackId)
  }

  function moveTrack(fromIdx: number, toIdx: number) {
    const t = tracks.value.splice(fromIdx, 1)[0]
    if (t) tracks.value.splice(toIdx, 0, t)
  }

  function clearTracks() {
    tracks.value = []
  }

  return {
    savedClips, addClip, removeClip,
    tracks, addTrack, removeTrack, moveTrack, clearTracks,
  }
})
