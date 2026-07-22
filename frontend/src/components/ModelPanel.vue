<script setup lang="ts">
import { ref, computed } from 'vue'
import { useModelStore } from '../stores/modelStore'
import { useLocaleStore } from '../stores/localeStore'
import { profileApi } from '../api'

const modelStore = useModelStore()
const localeStore = useLocaleStore()
const t = computed(() => localeStore.t)
const t2sInput = ref<HTMLInputElement | null>(null)
const vitsInput = ref<HTMLInputElement | null>(null)

// 上传新音色弹窗
const showNewProfile = ref(false)
const uploadStep = ref<'form' | 'uploading'>('form')
const newName = ref('')
const newDesc = ref('')
const newT2sFile = ref<File | null>(null)
const newVitsFile = ref<File | null>(null)
const newAvatarFile = ref<File | null>(null)
const avatarPreview = ref<string>('')

function openUploadModal() {
  newName.value = ''
  newDesc.value = ''
  newT2sFile.value = null
  newVitsFile.value = null
  newAvatarFile.value = null
  avatarPreview.value = ''
  uploadStep.value = 'form'
  showNewProfile.value = true
}

function onProfileSelect(e: Event) {
  const id = (e.target as HTMLSelectElement).value
  if (id) modelStore.selectProfile(id)
}

async function onT2sUpload(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) await modelStore.uploadModel(file)
}
async function onVitsUpload(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) await modelStore.uploadModel(file)
}

function onT2sPicked(e: Event) {
  newT2sFile.value = (e.target as HTMLInputElement).files?.[0] || null
}
function onVitsPicked(e: Event) {
  newVitsFile.value = (e.target as HTMLInputElement).files?.[0] || null
}
function onAvatarPicked(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  newAvatarFile.value = file
  const reader = new FileReader()
  reader.onload = () => { avatarPreview.value = reader.result as string }
  reader.readAsDataURL(file)
}

async function doCreateProfile() {
  if (!newName.value.trim() || !newT2sFile.value || !newVitsFile.value) return
  uploadStep.value = 'uploading'

  // 1. 上传两个模型文件
  const savedT2s = await modelStore.uploadModel(newT2sFile.value)
  const savedVits = await modelStore.uploadModel(newVitsFile.value)
  if (!savedT2s || !savedVits) {
    uploadStep.value = 'form'
    return
  }

  // 2. 上传头像（如果有）
  let imageName: string | null = null
  if (newAvatarFile.value) {
    try {
      const imgRes = await profileApi.uploadImage(newAvatarFile.value)
      imageName = (imgRes.data as { filename: string }).filename
    } catch { /* ignored */ }
  }

  // 3. 创建配对
  await modelStore.createProfile(
    newName.value.trim(),
    newDesc.value.trim(),
    savedT2s,
    savedVits,
    imageName,
  )

  // 4. 自动选中并加载
  const latest = modelStore.profiles.find(
    p => p.t2s_file === savedT2s && p.vits_file === savedVits,
  )
  if (latest) {
    modelStore.selectProfile(latest.id)
    await modelStore.loadSelected()
  }

  uploadStep.value = 'form'
  showNewProfile.value = false
}
</script>

<template>
  <div class="panel model-panel">
    <div class="panel-header">{{ t.modelPanel.title }}</div>

    <!-- 音色选择 -->
    <div class="field">
      <label>{{ t.modelPanel.selectProfile }}</label>
      <select class="field-select" @change="onProfileSelect" :value="modelStore.selectedProfileId">
        <option value="">{{ t.modelPanel.selectPlaceholder }}</option>
        <option v-for="p in modelStore.profiles" :key="p.id" :value="p.id">
          {{ p.name }}
        </option>
      </select>
    </div>

    <div class="or-divider">{{ t.modelPanel.or }}</div>

    <button class="btn btn-accent btn-sm" @click="openUploadModal">{{ t.modelPanel.uploadNew }}</button>

    <!-- 高级：手动选文件 -->
    <details class="advanced-toggle">
      <summary>{{ t.modelPanel.advanced }}</summary>
      <div class="field" style="margin-top: 8px">
        <label>{{ t.modelPanel.t2sLabel }}</label>
        <div class="field-row">
          <select v-model="modelStore.selectedT2s" class="field-select">
            <option value="">{{ localeStore.t.voiceModal.selectFile }}…</option>
            <option v-for="m in modelStore.t2sModels" :key="m.path" :value="m.filename">{{ m.filename }}</option>
          </select>
          <button class="btn btn-ghost btn-sm upload-dot" @click="t2sInput?.click()" :title="localeStore.t.voiceModal.selectFile">+</button>
          <input ref="t2sInput" type="file" accept=".ckpt" hidden @change="onT2sUpload" />
        </div>
      </div>
      <div class="field">
        <label>{{ t.modelPanel.vitsLabel }}</label>
        <div class="field-row">
          <select v-model="modelStore.selectedVits" class="field-select">
            <option value="">{{ localeStore.t.voiceModal.selectFile }}…</option>
            <option v-for="m in modelStore.vitsModels" :key="m.path" :value="m.filename">{{ m.filename }}</option>
          </select>
          <button class="btn btn-ghost btn-sm upload-dot" @click="vitsInput?.click()" :title="localeStore.t.voiceModal.selectFile">+</button>
          <input ref="vitsInput" type="file" accept=".pth" hidden @change="onVitsUpload" />
        </div>
      </div>
    </details>

    <button
      class="btn btn-primary"
      :class="{ loading: modelStore.isLoading }"
      :disabled="!modelStore.selectedT2s || !modelStore.selectedVits || modelStore.isLoading"
      @click="modelStore.loadSelected()"
    >
      <span v-if="modelStore.isLoading" class="spinner"></span>
      {{ modelStore.isLoading ? t.modelPanel.loading : t.modelPanel.loadModel }}
    </button>

    <p v-if="modelStore.loadError" class="error-msg">{{ modelStore.loadError }}</p>

    <!-- 上传新音色弹窗（Teleport 到 body，全屏居中） -->
    <Teleport to="body">
      <div v-if="showNewProfile" class="modal-overlay" @click.self="showNewProfile = false">
        <div class="upload-modal">
        <h3>{{ t.voiceModal.title }}</h3>

        <!-- 头像 -->
        <div class="um-avatar-wrap">
          <div class="um-avatar" :class="{ hasImg: !!avatarPreview }">
            <img v-if="avatarPreview" :src="avatarPreview" alt="" />
            <span v-else>{{ newName.trim() ? newName.trim().charAt(0) : '?' }}</span>
          </div>
          <label class="um-avatar-upload">
            {{ t.voiceModal.uploadAvatar }}
            <input type="file" accept="image/*" hidden @change="onAvatarPicked" />
          </label>
        </div>

        <!-- 名字 -->
        <label>{{ t.voiceModal.name }}</label>
        <input v-model="newName" :placeholder="t.voiceModal.namePlaceholder" maxlength="100" />

        <!-- 简介 -->
        <label>{{ t.voiceModal.description }}</label>
        <input v-model="newDesc" :placeholder="t.voiceModal.descPlaceholder" maxlength="500" />

        <!-- 模型文件 -->
        <div class="um-files">
          <div class="um-file-row">
            <label class="um-file-label">{{ t.voiceModal.t2sLabel }}</label>
            <button type="button" class="btn btn-ghost btn-sm um-file-btn" @click="($refs.mT2s as HTMLInputElement).click()">
              {{ newT2sFile ? newT2sFile.name : t.voiceModal.selectFile }}
            </button>
            <input ref="mT2s" type="file" accept=".ckpt" hidden @change="onT2sPicked" />
          </div>
          <div class="um-file-row">
            <label class="um-file-label">{{ t.voiceModal.vitsLabel }}</label>
            <button type="button" class="btn btn-ghost btn-sm um-file-btn" @click="($refs.mVits as HTMLInputElement).click()">
              {{ newVitsFile ? newVitsFile.name : t.voiceModal.selectFile }}
            </button>
            <input ref="mVits" type="file" accept=".pth" hidden @change="onVitsPicked" />
          </div>
        </div>

        <div class="um-actions">
          <button
            class="btn btn-primary"
            :disabled="uploadStep === 'uploading' || !newName.trim() || !newT2sFile || !newVitsFile"
            @click="doCreateProfile"
          >
            {{ uploadStep === 'uploading' ? t.voiceModal.uploading : t.voiceModal.createAndLoad }}
          </button>
          <button class="btn btn-ghost" @click="showNewProfile = false">{{ t.voiceModal.cancel }}</button>
        </div>
      </div>
    </div>
    </Teleport>
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
  font-size: 16px; line-height: 1; padding: 4px 8px; font-weight: 300; color: var(--c-text-secondary);
}
.upload-dot:hover { color: var(--c-accent); }
.or-divider {
  text-align: center; font-size: 11px; color: var(--c-text-muted);
}
.advanced-toggle {
  font-size: 11px;
  color: var(--c-text-muted);
  cursor: pointer;
}
.advanced-toggle summary { margin-bottom: 4px; }

.spinner {
  display: inline-block; width: 14px; height: 14px;
  border: 2px solid transparent; border-top-color: currentColor;
  border-radius: 50%; animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.error-msg { font-size: 11px; color: var(--c-danger); line-height: 1.5; }

/* ---- Modal Overlay ---- */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: var(--c-bg-overlay);
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* ---- Upload Modal (dark) ---- */
.upload-modal {
  background: var(--c-bg-elevated);
  border: 1px solid var(--c-border);
  border-radius: var(--radius-xl);
  padding: 36px;
  width: 420px;
  max-height: 90vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.upload-modal h3 {
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 700;
  text-align: center;
  margin-bottom: 4px;
  color: var(--c-text);
}
.upload-modal label {
  font-size: 12px;
  font-weight: 600;
  color: var(--c-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* avatar */
.um-avatar-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}
.um-avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  overflow: hidden;
  border: 2px solid var(--c-border);
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(124, 252, 0, 0.04);
  font-family: var(--font-display);
  font-size: 32px;
  font-weight: 700;
  color: var(--c-accent);
  text-transform: uppercase;
}
.um-avatar.hasImg { border-color: var(--c-accent); }
.um-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.um-avatar-upload {
  font-size: 12px;
  color: var(--c-accent);
  cursor: pointer;
  text-decoration: underline;
}

/* inputs */
.upload-modal input[type="text"],
.upload-modal input[type="text"]:focus {
  width: 100%;
  font-family: inherit;
  font-size: 14px;
  padding: 10px 14px;
  background: var(--c-bg-input);
  border: 1px solid var(--c-border);
  border-radius: var(--radius-sm);
  color: var(--c-text);
}
.upload-modal input::placeholder { color: var(--c-text-muted); }

/* file rows */
.um-files {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.um-file-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.um-file-label {
  font-size: 13px;
  color: var(--c-text-secondary);
  text-transform: none;
  letter-spacing: normal;
  font-weight: 400;
}
.um-file-btn {
  font-size: 12px;
  max-width: 60%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.um-actions {
  display: flex;
  gap: 10px;
  margin-top: 8px;
}

/* accent button */
.btn-accent {
  background: var(--c-accent-bg);
  color: var(--c-accent);
  border: 1px solid rgba(124, 252, 0, 0.2);
  border-radius: var(--radius-sm);
  padding: 6px 16px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  font-family: var(--font-body);
}
.btn-accent:hover {
  background: var(--c-accent-bg-2);
  border-color: var(--c-accent);
}
</style>