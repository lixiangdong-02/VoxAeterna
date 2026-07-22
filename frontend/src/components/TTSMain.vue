<script setup lang="ts">
import { computed, ref } from 'vue'
import { useTtsStore } from '../stores/ttsStore'
import { useModelStore } from '../stores/modelStore'
import { useHistoryStore } from '../stores/historyStore'
import { useUserStore } from '../stores/userStore'
import { useLocaleStore } from '../stores/localeStore'

const emit = defineEmits<{ upgrade: [] }>()

const ttsStore = useTtsStore()
const modelStore = useModelStore()
const historyStore = useHistoryStore()
const userStore = useUserStore()
const localeStore = useLocaleStore()
const t = computed(() => localeStore.t)

const trialBlocked = ref(false)

const canSynthesize = computed(() =>
  modelStore.isLoaded &&
  ttsStore.text.trim().length > 0 &&
  ttsStore.refAudioPath !== '' &&
  ttsStore.taskState !== 'running'
)

const overLimit = computed(() => ttsStore.charCount > ttsStore.maxChars)

async function onSynthesize() {
  trialBlocked.value = false

  if (userStore.subscriptionPlan === 'free') {
    if (userStore.trialRemaining !== null && userStore.trialRemaining <= 0) {
      trialBlocked.value = true
      return
    }
  }

  await ttsStore.startSynthesis()

  if (ttsStore.taskState === 'done') {
    if (userStore.subscriptionPlan === 'free') {
      await userStore.consumeTrial()
    }
    const { useAuthStore } = await import('@/stores/authStore')
    historyStore.refresh(useAuthStore().user?.id || 0)
  }
}

const stateConfig = computed(() => {
  switch (ttsStore.taskState) {
    case 'running': return { label: t.value.tts.synthesizing, cls: 'running' }
    case 'done': return { label: t.value.tts.done, cls: 'done' }
    case 'error': return { label: t.value.tts.failed, cls: 'error' }
    default: return { label: '', cls: '' }
  }
})
</script>

<template>
  <div class="panel tts-main">
    <div class="main-header">
      <span class="panel-header" style="margin-bottom: 0">{{ t.tts.title }}</span>
      <span class="char-count" :class="{ over: overLimit }">
        {{ ttsStore.charCount }}<span class="char-limit"> / {{ ttsStore.maxChars }}</span>
      </span>
    </div>

    <textarea
      v-model="ttsStore.text"
      class="tts-textarea"
      rows="4"
      :placeholder="t.tts.placeholder"
      @input="ttsStore.updateCharCount(($event.target as HTMLTextAreaElement).value)"
    ></textarea>

    <div class="tts-actions">
      <button
        class="btn btn-primary"
        :disabled="!canSynthesize || overLimit"
        @click="onSynthesize"
      >
        {{ t.tts.synthesize }}
      </button>
      <button
        v-if="ttsStore.taskState === 'running'"
        class="btn btn-ghost"
        @click="ttsStore.cancelTask()"
      >{{ t.tts.cancel }}</button>
      <span
        v-if="stateConfig.cls"
        class="tts-state"
        :class="stateConfig.cls"
      >{{ stateConfig.label }}</span>
    </div>

    <p v-if="trialBlocked" class="trial-msg">
      {{ t.tts.trialExhausted }}
      <a href="#" @click.prevent="emit('upgrade')">{{ t.tts.upgrade }}</a>
    </p>
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
  background: var(--c-bg-input);
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
.tts-state.running { color: var(--c-amber); background: var(--c-amber-bg); }
.tts-state.done { color: var(--c-accent); background: var(--c-accent-bg); }
.tts-state.error { color: var(--c-danger); background: rgba(224, 82, 61, 0.1); }

.error-msg { font-size: 11px; color: var(--c-danger); }
.trial-msg {
  font-size: 12px;
  color: var(--c-amber);
  background: var(--c-amber-bg);
  padding: 8px 12px;
  border-radius: var(--radius-sm);
}
.trial-msg a {
  color: var(--c-accent);
  text-decoration: underline;
}
</style>
