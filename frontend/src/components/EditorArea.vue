<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import WaveSurfer from 'wavesurfer.js'
import { useClipStore } from '../stores/clipStore'
import { useLocaleStore } from '../stores/localeStore'
import type { EditorTrack, SavedClip } from '../types'

const clipStore = useClipStore()
const localeStore = useLocaleStore()
const t = computed(() => localeStore.t)

// ===== 波形容器 =====
const waveformRef = ref<HTMLDivElement | null>(null)
let ws: WaveSurfer | null = null

// 当前预览的轨道
const activeTrackIdx = ref(-1)
const playing = ref(false)
const exportFormat = ref<'wav' | 'mp3'>('wav')

function formatDuration(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function totalDuration(): number {
  return clipStore.tracks.reduce((sum, t) => sum + (t.endOffset - t.startOffset), 0)
}

// ===== WaveSurfer =====
onMounted(() => {
  if (!waveformRef.value) return
  ws = WaveSurfer.create({
    container: waveformRef.value,
    waveColor: 'rgba(255, 255, 255, 0.06)',
    progressColor: '#7CFC00',
    cursorColor: 'rgba(124, 252, 0, 0.6)',
    height: 120,
    barWidth: 2,
    barGap: 1.5,
    barRadius: 1,
    normalize: true,
    backend: 'WebAudio',
  })
  ws.on('play', () => (playing.value = true))
  ws.on('pause', () => (playing.value = false))
  ws.on('finish', () => {
    playing.value = false
    // 自动播放下一个
    if (activeTrackIdx.value < clipStore.tracks.length - 1) {
      activeTrackIdx.value++
      playTrack(activeTrackIdx.value)
    } else {
      activeTrackIdx.value = -1
    }
  })
})

onUnmounted(() => ws?.destroy())

function playTrack(idx: number) {
  if (!ws || idx < 0 || idx >= clipStore.tracks.length) return
  const t = clipStore.tracks[idx]
  if (t.url) {
    activeTrackIdx.value = idx
    ws.load(t.url)
    ws.once('ready', () => ws?.play())
  }
}

function togglePlayAll() {
  if (playing.value) {
    ws?.pause()
    return
  }
  if (clipStore.tracks.length === 0) return
  // 从当前轨或第一轨开始
  const start = activeTrackIdx.value >= 0 ? activeTrackIdx.value : 0
  playTrack(start)
}

// ===== 拖入 =====
function onDragOver(e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'
}

function onDrop(e: DragEvent) {
  e.preventDefault()
  const clipId = e.dataTransfer?.getData('application/clip-id')
  if (!clipId) return
  const clip = clipStore.savedClips.find(c => c.id === clipId)
  if (clip) {
    clipStore.addTrack(clip)
  }
}

// ===== 拼接合并导出 =====
async function mergeAndExport() {
  if (clipStore.tracks.length === 0) return

  const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext
  const ctx = new AudioContextClass()
  const buffers: AudioBuffer[] = []

  for (const track of clipStore.tracks) {
    const res = await fetch(track.url)
    const arrayBuf = await res.arrayBuffer()
    const audioBuf = await ctx.decodeAudioData(arrayBuf)
    buffers.push(audioBuf)
  }

  const totalLen = buffers.reduce((sum, b) => sum + b.length, 0)
  const out = ctx.createBuffer(1, totalLen, buffers[0]?.sampleRate || 22050)
  const outData = out.getChannelData(0)

  let offset = 0
  for (const buf of buffers) {
    outData.set(buf.getChannelData(0), offset)
    offset += buf.length
  }

  // 导出为 WAV blob
  const wavBlob = audioBufferToWavBlob(out)
  const url = URL.createObjectURL(wavBlob)
  const a = document.createElement('a')
  a.href = url
  a.download = `voxaeterna_merged.${exportFormat.value}`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  ctx.close()
}

function audioBufferToWavBlob(buffer: AudioBuffer): Blob {
  const numChannels = buffer.numberOfChannels
  const sampleRate = buffer.sampleRate
  const length = buffer.length
  const bytesPerSample = 2
  const blockAlign = numChannels * bytesPerSample
  const byteRate = sampleRate * blockAlign
  const dataSize = length * blockAlign
  const headerSize = 44
  const totalSize = headerSize + dataSize

  const arrBuf = new ArrayBuffer(totalSize)
  const view = new DataView(arrBuf)

  function writeString(offset: number, str: string) {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i))
    }
  }

  writeString(0, 'RIFF')
  view.setUint32(4, totalSize - 8, true)
  writeString(8, 'WAVE')
  writeString(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, numChannels, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, byteRate, true)
  view.setUint16(32, blockAlign, true)
  view.setUint16(34, bytesPerSample * 8, true)
  writeString(36, 'data')
  view.setUint32(40, dataSize, true)

  const channelData = buffer.getChannelData(0)
  let offset = 44
  for (let i = 0; i < length; i++) {
    const sample = Math.max(-1, Math.min(1, channelData[i]))
    const int16 = sample < 0 ? sample * 0x8000 : sample * 0x7FFF
    view.setInt16(offset, int16, true)
    offset += 2
  }

  return new Blob([arrBuf], { type: 'audio/wav' })
}

// ===== 拖拽排序 =====
let dragIdx = -1

function onTrackDragStart(idx: number) {
  dragIdx = idx
}

function onTrackDragOver(e: DragEvent) {
  e.preventDefault()
}

function onTrackDrop(idx: number) {
  if (dragIdx >= 0 && dragIdx !== idx) {
    clipStore.moveTrack(dragIdx, idx)
  }
  dragIdx = -1
}
</script>

<template>
  <div class="panel editor-area" @dragover="onDragOver" @drop="onDrop">
    <div class="ed-top">
      <span class="panel-header editor-header">{{ t.editor.title }}</span>
      <span class="ed-total">{{ formatDuration(totalDuration()) }}</span>
    </div>

    <div class="ed-tracks" v-if="clipStore.tracks.length > 0">
      <div
        v-for="(track, idx) in clipStore.tracks"
        :key="track.id"
        class="ed-track"
        :class="{ active: idx === activeTrackIdx }"
        draggable="true"
        @dragstart="onTrackDragStart(idx)"
        @dragover="onTrackDragOver"
        @drop="onTrackDrop(idx)"
        @click="playTrack(idx)"
      >
        <span class="track-grip">⠿</span>
        <span class="track-name">{{ track.name }}</span>
        <span class="track-dur">{{ formatDuration(track.duration) }}</span>
        <button
          class="btn btn-ghost btn-sm track-remove"
          @click.stop="clipStore.removeTrack(track.id)"
        >✕</button>
      </div>
    </div>

    <div v-else class="ed-dropzone">
      {{ t.editor.dropHint }}
    </div>

    <div class="ed-waveform">
      <div ref="waveformRef" class="wave-inner"></div>
    </div>

    <div class="ed-actions">
      <button
        class="btn btn-primary btn-sm"
        :disabled="clipStore.tracks.length === 0"
        @click="togglePlayAll"
      >
        {{ playing ? t.editor.pause : t.editor.previewAll }}
      </button>
      <select v-model="exportFormat" class="ed-fmt">
        <option value="wav">WAV</option>
        <option value="mp3">MP3</option>
      </select>
      <button
        class="btn btn-ghost btn-sm"
        :disabled="clipStore.tracks.length === 0"
        @click="mergeAndExport"
      >{{ t.editor.mergeExport }}</button>
      <button
        v-if="clipStore.tracks.length > 0"
        class="btn btn-ghost btn-sm"
        @click="clipStore.clearTracks()"
      >{{ t.editor.clear }}</button>
    </div>
  </div>
</template>

<style scoped>
.editor-area {
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 100%;
}

.ed-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.editor-header { margin-bottom: 0; }
.ed-total {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--c-text-muted);
}

/* ---- 轨道列表 ---- */
.ed-tracks {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  max-height: 72px;
  overflow-y: auto;
}

.ed-track {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: var(--radius-sm);
  background: var(--c-bg-track);
  border: 1px solid var(--c-border);
  cursor: pointer;
  transition: all var(--duration-fast);
  white-space: nowrap;
}
.ed-track:hover { border-color: var(--c-border-active); }
.ed-track.active {
  border-color: var(--c-accent);
  background: var(--c-accent-bg);
}

.track-grip {
  color: var(--c-text-muted);
  cursor: grab;
  font-size: 14px;
  line-height: 1;
}
.track-name {
  font-size: 11px;
  color: var(--c-text);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.track-dur {
  font-size: 10px;
  color: var(--c-text-muted);
  font-family: var(--font-mono);
}
.track-remove {
  font-size: 10px;
  padding: 1px 4px;
}

/* ---- 拖放目标区 ---- */
.ed-dropzone {
  flex: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  border: 2px dashed var(--c-border-dash);
  border-radius: var(--radius-md);
  color: var(--c-text-muted);
  font-size: 13px;
  transition: border-color var(--duration-fast);
}
.editor-area:hover .ed-dropzone {
  border-color: var(--c-border-active);
}

/* ---- 波形 ---- */
.ed-waveform {
  flex: 1;
  min-height: 0;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--c-bg-waveform);
}
.wave-inner {
  width: 100%;
  height: 100%;
}

/* ---- 操作栏 ---- */
.ed-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.ed-fmt {
  font-size: 11px;
  padding: 4px 8px;
}
</style>
