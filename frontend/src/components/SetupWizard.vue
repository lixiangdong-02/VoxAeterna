<template>
  <Teleport to="body">
    <div v-if="visible && phase !== 'complete'" class="setup-overlay">
      <div class="setup-card">

        <!-- 检测中 -->
        <template v-if="phase === 'checking'">
          <div class="setup-icon"><span class="spinner" /></div>
          <h2>正在检查运行环境</h2>
          <p class="setup-desc">{{ statusLabel }}</p>
        </template>

        <!-- 没有 Python 运行时 -->
        <template v-else-if="phase === 'need-python'">
          <div class="setup-icon">🐍</div>
          <h2>缺少 Python 运行时</h2>
          <p class="setup-desc">
            请将 <strong>python-runtime.zip</strong> 解压到软件安装目录下的 <code>python</code> 文件夹中。<br /><br />
            例如：<code>F:\Sorf\VoxAeterna\python\python.exe</code><br /><br />
            然后重启本软件。
          </p>
          <div class="setup-actions">
            <button class="btn btn-primary" @click="handleRetry">重新检测</button>
            <button class="btn btn-ghost" @click="handleSkip">跳过</button>
          </div>
        </template>

        <!-- 需要下载模型 -->
        <template v-else-if="phase === 'need-models'">
          <div class="setup-icon">🧠</div>
          <h2>下载语音模型</h2>
          <p class="setup-desc">
            需要从魔搭社区下载语音合成模型（约 2.3GB）。<br />
            下载进度将实时显示。
          </p>
          <div class="setup-actions">
            <button class="btn btn-primary" @click="handleDownloadModels">开始下载</button>
            <button class="btn btn-ghost" @click="handleSkip">跳过</button>
          </div>
        </template>

        <!-- 下载中 -->
        <template v-else-if="phase === 'downloading'">
          <div class="setup-icon"><span class="spinner" /></div>
          <h2>{{ statusLabel }}</h2>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: downloadPercent + '%' }" />
          </div>
          <p class="progress-text">{{ downloadPercent }}%</p>
          <p v-if="modelDownloadFile" class="setup-desc">{{ modelDownloadFile }}</p>
        </template>

        <!-- 错误 -->
        <template v-else-if="phase === 'error'">
          <div class="setup-icon">❌</div>
          <h2>出错了</h2>
          <pre class="error-msg">{{ errorMessage }}</pre>
          <div class="setup-actions">
            <button class="btn btn-primary" @click="handleRetry">重试</button>
            <button class="btn btn-ghost" @click="handleSkip">跳过</button>
          </div>
        </template>

      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const emit = defineEmits<{
  ready: []
  quit: []
}>()

type Phase =
  | 'checking'
  | 'need-python'
  | 'need-models'
  | 'downloading'
  | 'complete'
  | 'error'

const phase = ref<Phase>('checking')
const visible = ref(true)
const statusLabel = ref('正在检查环境...')
const downloadPercent = ref(0)
const errorMessage = ref('')
const modelDownloadFile = ref('')

let progressCleanup: (() => void) | null = null

onMounted(async () => {
  if (!window.envSetup) {
    phase.value = 'complete'
    emit('ready')
    return
  }

  window.envSetup.onProgress(handleProgress)
  progressCleanup = () => window.envSetup!.removeProgressListener()
  await checkEnvironment()
})

onUnmounted(() => { progressCleanup?.() })

function handleProgress(data: any) {
  switch (data.phase) {
    case 'downloading':
      phase.value = 'downloading'
      statusLabel.value = data.label || '正在下载...'
      downloadPercent.value = data.percent || 0
      modelDownloadFile.value = data.label || ''
      break
    case 'complete':
      phase.value = 'complete'
      statusLabel.value = '环境准备完成'
      break
    case 'error':
      phase.value = 'error'
      errorMessage.value = data.error || '未知错误'
      break
  }
}

async function checkEnvironment() {
  phase.value = 'checking'
  statusLabel.value = '正在检查环境...'

  try {
    const result = await window.envSetup!.check()

    if (!result.python) {
      phase.value = 'need-python'
      return
    }

    const hasModels = await window.envSetup!.checkModels()
    if (!hasModels) {
      phase.value = 'need-models'
      return
    }

    phase.value = 'complete'
    statusLabel.value = '环境准备完成！'
    emit('ready')
  } catch (e: any) {
    phase.value = 'error'
    errorMessage.value = e.message || '环境检测失败'
  }
}

async function handleDownloadModels() {
  try {
    const result = await window.envSetup!.downloadModels()
    if (!result.success) {
      phase.value = 'error'
      errorMessage.value = result.error || '模型下载失败'
      return
    }
    phase.value = 'complete'
    statusLabel.value = '环境准备完成！'
    emit('ready')
  } catch (e: any) {
    phase.value = 'error'
    errorMessage.value = e.message || '下载失败'
  }
}

async function handleRetry() {
  await checkEnvironment()
}

function handleSkip() {
  phase.value = 'complete'
  emit('ready')
}
</script>

<style scoped>
.setup-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 3000;
}

.setup-card {
  background: var(--c-bg-elevated);
  border: 1px solid var(--c-border);
  border-radius: var(--radius-lg);
  padding: 40px;
  width: 500px;
  max-width: 94vw;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  text-align: center;
}

.setup-icon { font-size: 48px; line-height: 1; }

.setup-card h2 {
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 700;
  color: var(--c-text);
  margin: 0;
}

.setup-desc {
  font-size: 14px;
  color: var(--c-text-secondary);
  line-height: 1.7;
  margin: 0;
}

.setup-desc code {
  font-family: var(--font-mono);
  font-size: 12px;
  background: rgba(0,0,0,0.3);
  padding: 2px 6px;
  border-radius: 3px;
  word-break: break-all;
}

.error-msg {
  color: var(--c-danger, #e74c3c);
  font-family: var(--font-mono);
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 200px;
  overflow-y: auto;
  text-align: left;
}

.setup-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.setup-actions .btn {
  padding: 10px 24px;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all var(--duration-fast);
  white-space: nowrap;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: var(--c-border);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--c-accent);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 13px;
  color: var(--c-text-muted);
  font-family: var(--font-mono);
  margin: 0;
}

.spinner {
  display: inline-block;
  width: 32px;
  height: 32px;
  border: 3px solid var(--c-border);
  border-top-color: var(--c-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.btn-primary { background: var(--c-accent); color: #0D0D0C; }
.btn-primary:hover { filter: brightness(1.15); }
.btn-ghost {
  background: transparent;
  color: var(--c-text-muted);
  border: 1px solid var(--c-border) !important;
}
.btn-ghost:hover { color: var(--c-text); border-color: var(--c-text-muted) !important; }
</style>
