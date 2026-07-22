<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import WaveSurfer from 'wavesurfer.js'
import { useTtsStore } from '../stores/ttsStore'
import { useLocaleStore } from '../stores/localeStore'

const ttsStore = useTtsStore()
const localeStore = useLocaleStore()
const t = computed(() => localeStore.t)
const container = ref<HTMLDivElement | null>(null)
const ws = ref<WaveSurfer | null>(null)
const playing = ref(false)

onMounted(() => {
  if (!container.value) return
  ws.value = WaveSurfer.create({
    container: container.value,
    waveColor: 'rgba(255, 255, 255, 0.06)',
    progressColor: '#7CFC00',
    cursorColor: 'rgba(124, 252, 0, 0.6)',
    height: 160,
    barWidth: 2.5,
    barGap: 1.5,
    barRadius: 2,
    normalize: true,
    backend: 'WebAudio',
  })
  ws.value.on('play', () => (playing.value = true))
  ws.value.on('pause', () => (playing.value = false))
  ws.value.on('finish', () => (playing.value = false))
})

onUnmounted(() => ws.value?.destroy())

watch(() => ttsStore.audioUrl, (url) => {
  if (url && ws.value) ws.value.load(url)
})

function togglePlay() { ws.value?.playPause() }

function exportAudio(format: 'wav' | 'mp3') {
  if (!ttsStore.audioBlob || !ttsStore.audioUrl) return
  const ext = format === 'mp3' ? '.mp3' : '.wav'
  const a = document.createElement('a')
  a.href = ttsStore.audioUrl
  a.download = `voxaeterna_output${ext}`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}
</script>

<template>
  <div class="panel timeline-panel">
    <div class="tl-top">
      <span class="panel-header" style="margin-bottom: 0">{{ t.timeline.title }}</span>
      <div class="tl-actions">
        <button
          class="btn btn-primary btn-sm"
          :disabled="!ttsStore.audioUrl"
          @click="togglePlay"
        >{{ playing ? t.timeline.pause : t.timeline.play }}</button>
        <button
          class="btn btn-ghost btn-sm"
          :disabled="!ttsStore.audioUrl"
          @click="exportAudio('wav')"
        >WAV</button>
        <button
          class="btn btn-ghost btn-sm"
          :disabled="!ttsStore.audioUrl"
          @click="exportAudio('mp3')"
        >MP3</button>
      </div>
    </div>

    <div class="waveform-wrap">
      <div v-if="!ttsStore.audioUrl" class="waveform-empty">
        {{ t.timeline.empty }}
      </div>
      <div ref="container" :class="{ hidden: !ttsStore.audioUrl }" class="waveform-container"></div>
    </div>
  </div>
</template>

<style scoped>
.timeline-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
}

.tl-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tl-actions {
  display: flex;
  gap: 6px;
}

.waveform-wrap {
  flex: 1;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--c-bg-waveform);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.waveform-empty {
  color: var(--c-text-muted);
  font-size: 13px;
}

.waveform-container {
  width: 100%;
  height: 100%;
}
.waveform-container.hidden { display: none; }
</style>
