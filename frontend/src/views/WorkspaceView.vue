<script setup lang="ts">
import { ref, onMounted } from 'vue'
import ModelPanel from '../components/ModelPanel.vue'
import ParamPanel from '../components/ParamPanel.vue'
import TTSMain from '../components/TTSMain.vue'
import TimelinePanel from '../components/TimelinePanel.vue'
import { useModelStore } from '../stores/modelStore'
import { useHistoryStore } from '../stores/historyStore'

const modelStore = useModelStore()
const historyStore = useHistoryStore()
const activeTab = ref<'project' | 'history'>('project')

onMounted(() => {
  modelStore.refreshList()
  historyStore.refresh()
})
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
        >项目</button>
        <button
          :class="{ active: activeTab === 'history' }"
          @click="activeTab = 'history'"
        >
          历史
          <span v-if="historyStore.records.length" class="tab-badge">{{ historyStore.records.length }}</span>
        </button>
      </nav>

      <div class="ws-status">
        <span
          class="state-dot"
          :class="{ loaded: modelStore.isLoaded, loading: modelStore.isLoading }"
        ></span>
        <span class="status-text">
          {{ modelStore.isLoading ? '加载中…' : modelStore.isLoaded ? '就绪' : '未加载' }}
        </span>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="ws-main" v-if="activeTab === 'project'">
      <div class="ws-top">
        <div class="ws-left">
          <ModelPanel />
        </div>
        <div class="ws-right">
          <ParamPanel />
          <TTSMain />
        </div>
      </div>
      <div class="ws-bottom">
        <TimelinePanel />
      </div>
    </main>

    <!-- 历史页面 -->
    <main class="ws-main" v-else>
      <div class="history-view panel">
        <div class="panel-header">合成历史</div>
        <div v-if="historyStore.records.length === 0" class="empty-state">
          暂无合成记录。创建您的第一个项目开始吧。
        </div>
        <div v-for="r in historyStore.records" :key="r.task_id" class="history-item">
          <div class="hi-left">
            <span class="hi-time">{{ r.created_at }}</span>
            <span class="hi-text">{{ r.text || '(无文本)' }}</span>
          </div>
          <div class="hi-right">
            <span class="hi-state" :class="r.state">{{ r.state }}</span>
            <span v-if="r.duration_seconds" class="hi-dur">{{ r.duration_seconds }}s</span>
            <button
              v-if="r.state === 'completed'"
              class="btn btn-ghost btn-sm"
              @click="historyStore.exportAudio(r.task_id, 'wav')"
            >导出</button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.workspace {
  height: 100%;
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
.ws-tabs button.active { background: rgba(124, 252, 0, 0.08); color: var(--c-accent); }
.tab-badge {
  background: var(--c-accent);
  color: #0A0A08;
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
  background: rgba(255, 255, 255, 0.15);
  transition: all var(--duration-normal);
}
.state-dot.loading { background: #F0A500; animation: pulse 1s ease-in-out infinite; }
.state-dot.loaded { background: var(--c-accent); box-shadow: 0 0 6px var(--c-accent-glow); animation: breathe 2s ease-in-out infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
@keyframes breathe { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }

.status-text {
  font-size: 11px;
  color: var(--c-text-muted);
  letter-spacing: 0.03em;
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
  overflow-y: auto;
}

.ws-right {
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

.ws-bottom {
  height: 220px;
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
