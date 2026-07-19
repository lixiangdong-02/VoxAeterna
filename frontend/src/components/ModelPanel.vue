<script setup lang="ts">
import { computed, ref } from 'vue'
import { useModelStore } from '../stores/modelStore'

const modelStore = useModelStore()

const t2sInput = ref<HTMLInputElement | null>(null)
const vitsInput = ref<HTMLInputElement | null>(null)

const canLoad = computed(() =>
  modelStore.selectedT2s && modelStore.selectedVits && !modelStore.isLoading
)

async function onT2sUpload(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) await modelStore.uploadModel(file)
}
async function onVitsUpload(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) await modelStore.uploadModel(file)
}
</script>

<template>
  <div class="panel model-panel">
    <div class="panel-header">模型</div>

    <!-- T2S -->
    <div class="field">
      <label>语义模型 · .ckpt</label>
      <div class="field-row">
        <select v-model="modelStore.selectedT2s" class="field-select">
          <option value="">选择文件…</option>
          <option v-for="m in modelStore.t2sModels" :key="m.path" :value="m.filename">
            {{ m.filename }}
          </option>
        </select>
        <button class="btn btn-ghost btn-sm upload-dot" @click="t2sInput?.click()" title="上传">+</button>
        <input ref="t2sInput" type="file" accept=".ckpt" hidden @change="onT2sUpload" />
      </div>
    </div>

    <!-- VITS -->
    <div class="field">
      <label>声学模型 · .pth</label>
      <div class="field-row">
        <select v-model="modelStore.selectedVits" class="field-select">
          <option value="">选择文件…</option>
          <option v-for="m in modelStore.vitsModels" :key="m.path" :value="m.filename">
            {{ m.filename }}
          </option>
        </select>
        <button class="btn btn-ghost btn-sm upload-dot" @click="vitsInput?.click()" title="上传">+</button>
        <input ref="vitsInput" type="file" accept=".pth" hidden @change="onVitsUpload" />
      </div>
    </div>

    <button
      class="btn btn-primary"
      :class="{ loading: modelStore.isLoading }"
      :disabled="!canLoad"
      @click="modelStore.loadSelected()"
    >
      <span v-if="modelStore.isLoading" class="spinner"></span>
      {{ modelStore.isLoading ? '加载中…' : '加载模型' }}
    </button>

    <p v-if="modelStore.loadError" class="error-msg">{{ modelStore.loadError }}</p>
  </div>
</template>

<style scoped>
.model-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-row {
  display: flex;
  gap: 6px;
  align-items: center;
}

.field-select {
  flex: 1;
}

.upload-dot {
  font-size: 16px;
  line-height: 1;
  padding: 4px 8px;
  font-weight: 300;
  color: var(--c-text-secondary);
}
.upload-dot:hover { color: var(--c-accent); }

.spinner {
  display: inline-block;
  width: 14px; height: 14px;
  border: 2px solid transparent;
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.error-msg {
  font-size: 11px;
  color: var(--c-danger);
  line-height: 1.5;
}
</style>
