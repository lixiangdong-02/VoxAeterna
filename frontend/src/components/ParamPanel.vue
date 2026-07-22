<script setup lang="ts">
import { ref, computed } from 'vue'
import { useTtsStore } from '../stores/ttsStore'
import { useLocaleStore } from '../stores/localeStore'

const ttsStore = useTtsStore()
const localeStore = useLocaleStore()
const t = computed(() => localeStore.t)
const refInput = ref<HTMLInputElement | null>(null)

async function onRefUpload(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) await ttsStore.uploadRefAudio(file)
}

const splitOpts = [
  { v: 'cut0', l: 'cut0 · Conservative' },
  { v: 'cut1', l: 'cut1' },
  { v: 'cut2', l: 'cut2' },
  { v: 'cut3', l: 'cut3' },
  { v: 'cut4', l: 'cut4' },
  { v: 'cut5', l: 'cut5 · Recommended' },
]
</script>

<template>
  <div class="panel param-panel">
    <div class="panel-header">{{ t.params.title }}</div>

    <!-- 参考音频 -->
    <div class="pa-group">
      <label>{{ t.params.refAudio }}</label>
      <div class="ref-row">
        <span class="ref-name">{{ ttsStore.refAudioFileName || t.params.notSelected }}</span>
        <button class="btn btn-ghost btn-sm" @click="refInput?.click()">{{ t.params.browse }}</button>
        <input ref="refInput" type="file" accept="audio/*" hidden @change="onRefUpload" />
      </div>
    </div>

    <!-- prompt_text -->
    <div class="pa-group">
      <label>{{ t.params.refText }}</label>
      <input
        v-model="ttsStore.promptText"
        type="text"
        :placeholder="t.params.refTextPlaceholder"
      />
    </div>

    <!-- 语速 -->
    <div class="pa-group">
      <div class="pa-label-row">
        <label>{{ t.params.speed }}</label>
        <span class="pa-val">{{ ttsStore.speedFactor.toFixed(1) }}x</span>
      </div>
      <input v-model.number="ttsStore.speedFactor" type="range" min="0.5" max="2.0" step="0.1" />
    </div>

    <!-- 断句 -->
    <div class="pa-group">
      <label>{{ t.params.split }}</label>
      <select v-model="ttsStore.splitMethod">
        <option v-for="o in splitOpts" :key="o.v" :value="o.v">{{ o.l }}</option>
      </select>
    </div>

    <!-- 高级 -->
    <button class="btn btn-ghost btn-sm pa-toggle" @click="ttsStore.showAdvanced = !ttsStore.showAdvanced">
      {{ ttsStore.showAdvanced ? t.params.collapse : t.params.advancedToggle }}
      <span class="toggle-arrow" :class="{ open: ttsStore.showAdvanced }">▾</span>
    </button>

    <div v-if="ttsStore.showAdvanced" class="pa-advanced">
      <div class="pa-group">
        <div class="pa-label-row"><label>top_k</label><span class="pa-val">{{ ttsStore.topK }}</span></div>
        <input v-model.number="ttsStore.topK" type="range" min="1" max="20" step="1" />
      </div>
      <div class="pa-group">
        <div class="pa-label-row"><label>top_p</label><span class="pa-val">{{ ttsStore.topP.toFixed(1) }}</span></div>
        <input v-model.number="ttsStore.topP" type="range" min="0" max="1" step="0.05" />
      </div>
      <div class="pa-group">
        <div class="pa-label-row"><label>temperature</label><span class="pa-val">{{ ttsStore.temperature.toFixed(1) }}</span></div>
        <input v-model.number="ttsStore.temperature" type="range" min="0.1" max="2.0" step="0.1" />
      </div>
      <div class="pa-group">
        <label>seed · {{ t.params.seed }}</label>
        <input v-model.number="ttsStore.seed" type="number" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.param-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.pa-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.pa-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.pa-val {
  font-size: 11px;
  font-weight: 600;
  color: var(--c-accent);
  font-family: var(--font-mono);
}

.ref-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.ref-name {
  flex: 1;
  font-size: 12px;
  color: var(--c-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pa-toggle {
  color: var(--c-text-muted);
  font-size: 11px;
  justify-content: flex-start;
  padding: 4px 0;
}
.pa-toggle:hover { color: var(--c-accent); }
.toggle-arrow {
  transition: transform var(--duration-fast);
  font-size: 10px;
}
.toggle-arrow.open { transform: rotate(180deg); }

.pa-advanced {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
</style>
