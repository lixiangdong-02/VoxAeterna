<script setup lang="ts">
import { computed } from 'vue'
import { useTtsStore } from '../stores/ttsStore'
import { useModelStore } from '../stores/modelStore'
import { useHistoryStore } from '../stores/historyStore'

const ttsStore = useTtsStore()
const modelStore = useModelStore()
const historyStore = useHistoryStore()

const canSynthesize = computed(() =>
  modelStore.isLoaded &&
  ttsStore.text.trim().length > 0 &&
  ttsStore.refAudioPath !== '' &&
  ttsStore.taskState !== 'running'
)

const overLimit = computed(() => ttsStore.charCount > ttsStore.maxChars)

async function onSynthesize() {
  await ttsStore.startSynthesis()
  if (ttsStore.taskState === 'done') historyStore.refresh()
}

const stateConfig = computed(() => {
  switch (ttsStore.taskState) {
    case 'running': return { label: '合成中…', cls: 'running' }
    case 'done': return { label: '完成', cls: 'done' }
    case 'error': return { label: '失败', cls: 'error' }
    default: return { label: '', cls: '' }
  }
})
</script>

<template>
  <div class="panel tts-main">
    <div class="main-header">
      <span class="panel-header" style="margin-bottom: 0">文本合成</span>
      <span class="char-count" :class="{ over: overLimit }">
        {{ ttsStore.charCount }}<span class="char-limit"> / {{ ttsStore.maxChars }}</span>
      </span>
    </div>

    <textarea
      v-model="ttsStore.text"
      class="tts-textarea"
      rows="4"
      placeholder="输入文字，即刻合成语音…"
      @input="ttsStore.updateCharCount(($event.target as HTMLTextAreaElement).value)"
    ></textarea>

    <div class="tts-actions">
      <button
        class="btn btn-primary"
        :disabled="!canSynthesize || overLimit"
        @click="onSynthesize"
      >
        开始合成
      </button>
      <button
        v-if="ttsStore.taskState === 'running'"
        class="btn btn-ghost"
        @click="ttsStore.cancelTask()"
      >取消</button>
      <span
        v-if="stateConfig.cls"
        class="tts-state"
        :class="stateConfig.cls"
      >{{ stateConfig.label }}</span>
    </div>

    <p v-if="ttsStore.taskError" class="error-msg">{{ ttsStore.taskError }}</p>
  </div>
</template>

<style scoped>
.tts-main {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
}

.main-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.char-count {
  font-family: var(--font-mono);
  font-size: 18px;
  font-weight: 500;
  color: var(--c-text);
}
.char-count.over { color: var(--c-danger); }
.char-limit {
  font-size: 12px;
  color: var(--c-text-muted);
  font-weight: 400;
}

.tts-textarea {
  flex: 1;
  min-height: 80px;
  font-size: 15px;
  line-height: 1.8;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--c-border);
  border-radius: var(--radius-md);
  padding: 16px;
  color: var(--c-text);
  resize: none;
}
.tts-textarea::placeholder { color: var(--c-text-muted); }
.tts-textarea:focus {
  border-color: var(--c-border-active);
  box-shadow: 0 0 0 1px var(--c-accent-glow);
  outline: none;
}

.tts-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.tts-state {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 3px 10px;
  border-radius: 100px;
}
.tts-state.running { color: #F0A500; background: rgba(240, 165, 0, 0.1); }
.tts-state.done { color: var(--c-accent); background: rgba(124, 252, 0, 0.08); }
.tts-state.error { color: var(--c-danger); background: rgba(224, 82, 61, 0.1); }

.error-msg { font-size: 11px; color: var(--c-danger); }
</style>
