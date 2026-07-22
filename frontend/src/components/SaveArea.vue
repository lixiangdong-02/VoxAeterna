<script setup lang="ts">
import { computed } from 'vue'
import { useClipStore } from '../stores/clipStore'
import { useLocaleStore } from '../stores/localeStore'
import type { SavedClip } from '../types'

const clipStore = useClipStore()
const localeStore = useLocaleStore()
const t = computed(() => localeStore.t)

function formatDuration(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function onDragStart(e: DragEvent, clip: SavedClip) {
  if (!e.dataTransfer) return
  e.dataTransfer.effectAllowed = 'copy'
  e.dataTransfer.setData('application/clip-id', clip.id)
}
</script>

<template>
  <div class="panel save-area">
    <div class="panel-header">
      {{ t.saveArea.title }}
      <span class="save-count">{{ clipStore.savedClips.length }}</span>
    </div>

    <div v-if="clipStore.savedClips.length === 0" class="save-empty">
      {{ t.saveArea.empty }}
    </div>

    <div
      v-for="clip in clipStore.savedClips"
      :key="clip.id"
      class="save-item"
      draggable="true"
      @dragstart="(e: DragEvent) => onDragStart(e, clip)"
    >
      <div class="save-info">
        <span class="save-name">{{ clip.name }}</span>
        <span class="save-dur">{{ formatDuration(clip.duration) }}</span>
      </div>
      <button
        class="btn btn-ghost btn-sm"
        :title="t.saveArea.remove"
        @click="clipStore.removeClip(clip.id)"
      >✕</button>
    </div>
  </div>
</template>

<style scoped>
.save-area {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 120px;
  max-height: 200px;
  overflow-y: auto;
}

.save-count {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--c-accent);
  background: var(--c-accent-bg);
  padding: 1px 6px;
  border-radius: 100px;
  margin-left: auto;
}

.save-empty {
  text-align: center;
  color: var(--c-text-muted);
  font-size: 12px;
  padding: 24px 0;
}

.save-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  background: var(--c-bg-track);
  border: 1px solid var(--c-border);
  cursor: grab;
  transition: border-color var(--duration-fast);
}
.save-item:hover {
  border-color: var(--c-border-active);
}
.save-item:active {
  cursor: grabbing;
}

.save-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}
.save-name {
  font-size: 12px;
  color: var(--c-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.save-dur {
  font-size: 10px;
  color: var(--c-text-muted);
  font-family: var(--font-mono);
}
</style>
