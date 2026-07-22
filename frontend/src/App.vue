<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterView } from 'vue-router'
import TitleBar from './components/TitleBar.vue'
import { versionApi } from '@/api'

const showUpdate = ref(false)
const updateInfo = ref({ version: '', download_url: '', changelog: '', force_update: false })

async function checkVersion() {
  try {
    const res = await versionApi.check()
    const latest = res.data

    // 获取当前版本（Electron 环境用 IPC，浏览器环境用默认值）
    let current = '0.0.0'
    if (window.appVersion) {
      current = await window.appVersion.get()
    }

    // 简单版本比较
    if (compareVersion(latest.version, current) > 0) {
      updateInfo.value = latest
      showUpdate.value = true
    }
  } catch {
    // 网络错误静默忽略
  }
}

function compareVersion(a: string, b: string): number {
  const pa = a.split('.').map(Number)
  const pb = b.split('.').map(Number)
  for (let i = 0; i < 3; i++) {
    if ((pa[i] || 0) > (pb[i] || 0)) return 1
    if ((pa[i] || 0) < (pb[i] || 0)) return -1
  }
  return 0
}

function openDownload() {
  if (window.appVersion && updateInfo.value.download_url) {
    window.appVersion.openUrl(updateInfo.value.download_url)
  }
}

function dismissUpdate() {
  showUpdate.value = false
}

onMounted(() => {
  checkVersion()
})
</script>

<template>
  <TitleBar />
  <main class="app-main">
    <RouterView />
  </main>

  <!-- 版本更新弹窗 -->
  <Teleport to="body">
    <div v-if="showUpdate" class="update-overlay" @click.self="!updateInfo.force_update && dismissUpdate()">
      <div class="update-card">
        <div class="update-header">
          <h2>发现新版本 v{{ updateInfo.version }}</h2>
          <button v-if="!updateInfo.force_update" class="btn-close" @click="dismissUpdate">&times;</button>
        </div>
        <div class="update-body">
          <p v-if="updateInfo.changelog" class="update-changelog">{{ updateInfo.changelog }}</p>
          <p v-else class="update-changelog">新版本可用，建议立即更新以获得最佳体验。</p>
        </div>
        <div class="update-footer">
          <button v-if="!updateInfo.force_update" class="btn btn-ghost" @click="dismissUpdate">稍后提醒</button>
          <button class="btn btn-primary" @click="openDownload">立即下载</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.app-main {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

/* 更新弹窗 */
.update-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}
.update-card {
  background: var(--c-bg-elevated);
  border: 1px solid var(--c-border);
  border-radius: var(--radius-lg);
  padding: 32px;
  width: 440px;
  max-width: 92vw;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.update-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.update-header h2 {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 700;
  color: var(--c-text);
}
.update-body {
  font-size: 14px;
  color: var(--c-text-secondary);
  line-height: 1.6;
}
.update-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
.update-footer .btn {
  padding: 10px 24px;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all var(--duration-fast);
}
.btn-primary {
  background: var(--c-accent);
  color: white;
}
.btn-primary:hover {
  background: var(--c-accent-hover);
}
.btn-ghost {
  background: transparent;
  color: var(--c-text-muted);
  border: 1px solid var(--c-border) !important;
}
.btn-ghost:hover {
  color: var(--c-text);
  border-color: var(--c-text-muted) !important;
}
.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  color: var(--c-text-muted);
  cursor: pointer;
  padding: 0 4px;
}
.btn-close:hover { color: var(--c-text); }
</style>