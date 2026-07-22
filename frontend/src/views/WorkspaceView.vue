<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import ModelPanel from '../components/ModelPanel.vue'
import ParamPanel from '../components/ParamPanel.vue'
import SaveArea from '../components/SaveArea.vue'
import TTSMain from '../components/TTSMain.vue'
import EditorArea from '../components/EditorArea.vue'
import UpgradeModal from '../components/UpgradeModal.vue'
import { useModelStore } from '../stores/modelStore'
import { useHistoryStore } from '../stores/historyStore'
import { useUserStore } from '../stores/userStore'
import { useAuthStore } from '../stores/authStore'
import { useLocaleStore } from '../stores/localeStore'

const modelStore = useModelStore()
const historyStore = useHistoryStore()
const userStore = useUserStore()
const authStore = useAuthStore()
const localeStore = useLocaleStore()
const t = computed(() => localeStore.t)
const _ = localeStore._
const activeTab = ref<'project' | 'history'>('project')
const showUpgrade = ref(false)

onMounted(() => {
  modelStore.refreshList()
  historyStore.refresh(authStore.user?.id || 0)
  userStore.fetchStatus()
})

function doLogout() {
  authStore.logout()
  window.location.hash = '/'
}
</script>

<template>
  <div class="workspace">
    <!-- 顶栏 -->
    <header class="ws-header">
      <div class="ws-brand" @click="$router.push('/')">
        <img src="/icon.png" alt="VoxAeterna" class="ws-icon" />
        <span class="ws-name">VoxAeterna</span>
      </div>

      <nav class="ws-tabs">
        <button
          :class="{ active: activeTab === 'project' }"
          @click="activeTab = 'project'"
        >{{ t.workspace.project }}</button>
        <button
          :class="{ active: activeTab === 'history' }"
          @click="activeTab = 'history'"
        >
          {{ t.workspace.history }}
          <span v-if="historyStore.records.length" class="tab-badge">{{ historyStore.records.length }}</span>
        </button>
      </nav>

      <div class="ws-status">
        <span v-if="userStore.trialRemaining !== null" class="trial-badge" @click="showUpgrade = true" style="cursor:pointer">
          {{ _('workspace.trialRemaining', { n: userStore.trialRemaining }) }}
        </span>
        <span v-if="userStore.subscriptionPlan !== 'free'" class="plan-badge">
          {{ userStore.subscriptionPlan === 'monthly' ? t.workspace.monthly : userStore.subscriptionPlan === 'yearly' ? t.workspace.yearly : t.workspace.lifetime }}
        </span>
        <span
          class="state-dot"
          :class="{ loaded: modelStore.isLoaded, loading: modelStore.isLoading }"
        ></span>
        <span class="status-text">
          {{ modelStore.isLoading ? t.workspace.loading : modelStore.isLoaded ? t.workspace.ready : t.workspace.notLoaded }}
        </span>
        <button class="btn btn-ghost btn-sm" @click="$router.push('/profile')" style="margin-right:4px">{{ t.workspace.profile }}</button>
        <button class="btn btn-ghost btn-sm ws-logout" @click="doLogout">{{ t.workspace.logout }}</button>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="ws-main" v-if="activeTab === 'project'">
      <div class="ws-top">
        <!-- 左列：模型 + 参数 -->
        <div class="ws-left">
          <ModelPanel />
          <ParamPanel />
        </div>
        <!-- 右列：保存区 + TTS -->
        <div class="ws-right">
          <SaveArea />
          <TTSMain @upgrade="showUpgrade = true" />
        </div>
      </div>
      <!-- 底部：编辑区 -->
      <div class="ws-bottom">
        <EditorArea />
      </div>
    </main>

    <!-- 历史页面 -->
    <main class="ws-main" v-else>
      <div class="history-view panel">
        <div class="panel-header">{{ t.historyView.title }}</div>
        <div v-if="historyStore.records.length === 0" class="empty-state">
          {{ t.historyView.empty }}
        </div>
        <div v-for="r in historyStore.records" :key="r.task_id" class="history-item">
          <div class="hi-left">
            <span class="hi-time">{{ r.created_at }}</span>
            <span class="hi-text">{{ r.text || t.historyView.noText }}</span>
          </div>
          <div class="hi-right">
            <span class="hi-state" :class="r.state">{{ r.state }}</span>
            <span v-if="r.duration_seconds" class="hi-dur">{{ r.duration_seconds }}s</span>
            <button
              v-if="r.state === 'completed'"
              class="btn btn-ghost btn-sm"
              @click="historyStore.exportAudio(r.task_id, 'wav')"
            >{{ t.historyView.export }}</button>
          </div>
        </div>
      </div>
    </main>
  </div>

  <UpgradeModal v-if="showUpgrade" @close="showUpgrade = false; userStore.fetchStatus()" />
</template>

<style scoped>
.workspace {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: var(--c-bg);
}

/* ---- Header ---- */
.ws-header {
  display: flex;
  align-items: center;
  padding: 0 20px;
  height: 48px;
  border-bottom: 1px solid var(--c-border);
  background: var(--c-bg-elevated);
  flex-shrink: 0;
  gap: 24px;
}

.ws-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}
.ws-icon { width: 24px; height: 24px; border-radius: 6px; }
.ws-name {
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--c-text);
}

.ws-tabs {
  display: flex;
  gap: 4px;
  flex: 1;
}
.ws-tabs button {
  background: transparent;
  border: none;
  color: var(--c-text-secondary);
  font-family: var(--font-body);
  font-size: 13px;
  padding: 6px 14px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--duration-fast);
  display: flex;
  align-items: center;
  gap: 6px;
}
.ws-tabs button:hover { background: var(--c-bg-glass); color: var(--c-text); }
.ws-tabs button.active { background: var(--c-accent-bg); color: var(--c-accent); }
.tab-badge {
  background: var(--c-accent);
  color: var(--c-btn-primary-text);
  font-size: 10px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}

.ws-status {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.state-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--c-bg-glass-hover);
  transition: all var(--duration-normal);
}
.state-dot.loading { background: var(--c-amber); animation: pulse 1s ease-in-out infinite; }
.state-dot.loaded { background: var(--c-accent); box-shadow: 0 0 6px var(--c-accent-glow); animation: breathe 2s ease-in-out infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
@keyframes breathe { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }

.status-text {
  font-size: 11px;
  color: var(--c-text-muted);
  letter-spacing: 0.03em;
}

.trial-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 100px;
  background: var(--c-accent-bg-2);
  color: var(--c-accent);
  white-space: nowrap;
}
.plan-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 100px;
  background: var(--c-amber-bg);
  color: var(--c-amber);
  white-space: nowrap;
}
.ws-logout {
  font-size: 11px;
  padding: 2px 10px;
}

/* ---- Main Layout ---- */
.ws-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 16px;
  gap: 16px;
}

.ws-top {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

.ws-left {
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

.ws-right {
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

.ws-bottom {
  height: 280px;
  flex-shrink: 0;
}

/* ---- History view ---- */
.history-view {
  flex: 1;
  overflow-y: auto;
}
.empty-state {
  text-align: center;
  color: var(--c-text-muted);
  padding: 60px 0;
  font-size: 14px;
}
.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid var(--c-border);
}
.history-item:last-child { border-bottom: none; }
.hi-left { display: flex; flex-direction: column; gap: 2px; }
.hi-time { font-size: 11px; color: var(--c-text-muted); font-family: var(--font-mono); }
.hi-text { font-size: 13px; color: var(--c-text); max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.hi-right { display: flex; align-items: center; gap: 12px; }
.hi-state {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.hi-state.completed { color: var(--c-accent); }
.hi-state.failed { color: var(--c-danger); }
.hi-state.cancelled { color: var(--c-text-muted); }
.hi-dur { font-size: 11px; color: var(--c-text-secondary); font-family: var(--font-mono); }
</style>
