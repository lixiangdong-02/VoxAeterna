<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'
import { useModelStore } from '@/stores/modelStore'
import { useHistoryStore } from '@/stores/historyStore'
import { useUserStore } from '@/stores/userStore'
import { useLocaleStore } from '@/stores/localeStore'
import { profileApi } from '@/api'
import gsap from 'gsap'
import HomeBackground from '@/components/HomeBackground.vue'

const router = useRouter()
const authStore = useAuthStore()
const modelStore = useModelStore()
const historyStore = useHistoryStore()
const userStore = useUserStore()
const localeStore = useLocaleStore()
const t = computed(() => localeStore.t)
const _ = localeStore._

const heroRef = ref<HTMLElement | null>(null)
const isHovering = ref(false)
const showDashboard = computed(() => authStore.isLoggedIn)

// 上传新音色弹窗
const showUploadModal = ref(false)
const uploadStep = ref<'form' | 'uploading'>('form')
const newName = ref('')
const newDesc = ref('')
const newT2sFile = ref<File | null>(null)
const newVitsFile = ref<File | null>(null)
const newAvatarFile = ref<File | null>(null)
const avatarPreview = ref<string>('')

onMounted(async () => {
  if (heroRef.value) {
    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } })
    const children = heroRef.value.querySelectorAll('.hero-item')
    tl.fromTo(children, { opacity: 0, y: 28 }, { opacity: 1, y: 0, stagger: 0.12, duration: 0.8 })
  }
  if (localStorage.getItem('vox_token')) {
    await authStore.restoreSession()
  }
  if (authStore.isLoggedIn) {
    await Promise.all([
      modelStore.refreshList(),
      historyStore.refresh(authStore.user!.id),
      userStore.fetchStatus(),
    ])
  }
})

function goWorkspace() {
  router.push('/workspace')
}

function doLogout() {
  authStore.logout()
  historyStore.records = []
  window.location.hash = '/'
}

function openUploadModal() {
  newName.value = ''
  newDesc.value = ''
  newT2sFile.value = null
  newVitsFile.value = null
  newAvatarFile.value = null
  avatarPreview.value = ''
  uploadStep.value = 'form'
  showUploadModal.value = true
}

function onAvatarPicked(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  newAvatarFile.value = file
  const reader = new FileReader()
  reader.onload = () => { avatarPreview.value = reader.result as string }
  reader.readAsDataURL(file)
}

function onT2sPicked(e: Event) {
  newT2sFile.value = (e.target as HTMLInputElement).files?.[0] || null
}

function onVitsPicked(e: Event) {
  newVitsFile.value = (e.target as HTMLInputElement).files?.[0] || null
}

async function doUploadAndCreate() {
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
    } catch { /* 头像上传失败不影响创建 */ }
  }

  // 3. 创建配对
  await modelStore.createProfile(
    newName.value.trim(),
    newDesc.value.trim(),
    savedT2s,
    savedVits,
    imageName,
  )

  uploadStep.value = 'form'
  showUploadModal.value = false
}

async function loadProfile(profileId: string) {
  modelStore.selectProfile(profileId)
  await modelStore.loadSelected()
  if (modelStore.isLoaded) router.push('/workspace')
}

function onHistoryClick(record: any) {
  import('@/stores/ttsStore').then(({ useTtsStore }) => {
    useTtsStore().loadFromHistory(record)
  })
  router.push('/workspace')
}

function exportAudio(taskId: string) {
  historyStore.exportAudio(taskId, 'wav')
}

async function deleteHistory(taskId: string) {
  if (!authStore.user) return
  await historyStore.deleteRecord(taskId, authStore.user.id)
}

function getImageUrl(profile: typeof modelStore.profiles[0]): string {
  if (profile.image) {
    return `http://127.0.0.1:9880/api/profiles/image/${encodeURIComponent(profile.image)}`
  }
  return ''
}

const BASE_URL = 'http://127.0.0.1:9880/api'
</script>

<template>
  <div class="home" :class="{ scrolled: showDashboard }">
    <!-- 背景 -->
    <HomeBackground />

    <!-- Hero 区 -->
    <div ref="heroRef" class="hero">
      <img src="/icon.png" alt="VoxAeterna" class="hero-logo hero-item" />
      <div class="hero-badge hero-item">{{ t.app.tagline }}</div>
      <h1 class="hero-title hero-item">{{ t.app.title }}</h1>
      <p class="hero-desc hero-item">
        {{ t.app.description }}
      </p>

      <!-- 未登录 -->
      <template v-if="!authStore.isLoggedIn">
        <div class="hero-features hero-item">
          <div class="feature"><span class="feature-num">v2</span><span class="feature-label">{{ t.hero.featureEngine }}</span></div>
          <span class="feature-sep">·</span>
          <div class="feature"><span class="feature-num">{{ t.hero.featureLocal }}</span><span class="feature-label">{{ t.hero.featureOffline }}</span></div>
          <span class="feature-sep">·</span>
          <div class="feature"><span class="feature-num">{{ t.hero.featureWaveform }}</span><span class="feature-label">{{ t.hero.featureEdit }}</span></div>
        </div>
        <button
          class="btn btn-primary btn-lg hero-cta hero-item"
          :class="{ hovering: isHovering }"
          @mouseenter="isHovering = true" @mouseleave="isHovering = false"
          @click="goWorkspace"
        ><span class="cta-icon">+</span> {{ t.hero.createProject }}</button>
        <div class="hero-nav hero-item">
          <button class="btn btn-primary btn-lg" @click="$router.push('/login')">{{ t.hero.login }}</button>
          <button class="btn btn-ghost" @click="$router.push('/register')">{{ t.hero.register }}</button>
        </div>
        <p class="hero-version hero-item">{{ t.hero.gpuNotice }}</p>
      </template>

      <!-- 已登录 -->
      <template v-else>
        <div class="hero-actions hero-item">
          <button class="btn btn-primary btn-lg" @click="goWorkspace">{{ t.hero.enterWorkspace }}</button>
          <button class="btn btn-ghost" @click="$router.push('/profile')">{{ t.hero.profile }}</button>
          <button class="btn btn-ghost" @click="doLogout">{{ t.hero.logout }}</button>
          <span v-if="userStore.trialRemaining !== null" class="trial-badge">
            {{ _('hero.trialRemaining', { n: userStore.trialRemaining }) }}
          </span>
        </div>
      </template>

      <!-- 向下滚动提示 -->
      <div v-if="showDashboard" class="scroll-hint hero-item">{{ t.hero.scrollHint }}</div>
    </div>

    <!-- Dashboard 区 -->
    <div v-if="showDashboard" class="dashboard">
      <main class="dash-main">
        <!-- 我的音色 -->
        <section class="dash-section">
          <div class="section-head">
            <h2>{{ t.dashboard.myVoices }}</h2>
            <button class="btn btn-accent btn-sm" @click="openUploadModal">
              {{ t.dashboard.createNewVoice }}
            </button>
          </div>

          <div v-if="modelStore.profiles.length === 0" class="empty-state">
            <p>{{ t.dashboard.noVoices }}</p>
            <button class="btn btn-primary" style="margin-top:16px" @click="openUploadModal">{{ t.dashboard.createNewVoice }}</button>
          </div>

          <div class="profile-grid">
            <div
              v-for="p in modelStore.profiles" :key="p.id"
              class="profile-card"
              @click="loadProfile(p.id)"
            >
              <div class="pc-avatar" v-if="p.image">
                <img :src="`${BASE_URL}/profiles/image/${encodeURIComponent(p.image)}`" alt="" />
              </div>
              <div class="pc-avatar placeholder" v-else>
                {{ p.name.charAt(0) }}
              </div>
              <div class="pc-name">{{ p.name }}</div>
              <div class="pc-desc" v-if="p.description">{{ p.description }}</div>
            </div>

            <!-- 新建按钮卡片 -->
            <div class="profile-card add-card" @click="openUploadModal">
              <div class="pc-avatar add-avatar">+</div>
              <div class="pc-name">{{ t.dashboard.createNewVoice }}</div>
            </div>
          </div>
        </section>

        <!-- 最近合成 -->
        <section class="dash-section">
          <div class="section-head">
            <h2>{{ t.dashboard.recentSynthesis }}</h2>
            <router-link to="/workspace" class="btn btn-ghost btn-sm">{{ t.dashboard.viewAll }}</router-link>
          </div>

          <div v-if="historyStore.records.length === 0" class="empty-state">
            {{ t.dashboard.noHistory }}
          </div>

          <div class="history-list">
            <div
              v-for="r in historyStore.records" :key="r.task_id"
              class="history-card"
              @click="onHistoryClick(r)"
            >
              <div class="hc-left">
                <span class="hc-text">{{ r.text || t.dashboard.noText }}</span>
                <span class="hc-meta">{{ r.created_at }} · {{ r.duration_seconds?.toFixed(1) || '?' }}s</span>
              </div>
              <div class="hc-actions" @click.stop>
                <button class="btn btn-ghost btn-sm" @click="exportAudio(r.task_id)" :title="t.dashboard.export">▶️</button>
                <button class="btn btn-ghost btn-sm" @click="deleteHistory(r.task_id)" :title="t.dashboard.delete">🗑️</button>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>

    <!-- 上传新音色弹窗（Teleport 到 body，全屏居中） -->
    <Teleport to="body">
      <div v-if="showUploadModal" class="modal-overlay" @click.self="showUploadModal = false">
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
        <input v-model="newName" class="um-input" :placeholder="t.voiceModal.namePlaceholder" maxlength="100" />

        <!-- 简介 -->
        <label>{{ t.voiceModal.description }}</label>
        <input v-model="newDesc" class="um-input" :placeholder="t.voiceModal.descPlaceholder" maxlength="500" />

        <!-- 模型文件 -->
        <div class="um-files">
          <div class="um-file-row">
            <label class="um-file-label">{{ t.voiceModal.t2sLabel }}</label>
            <button class="btn btn-ghost btn-sm um-file-btn" @click="($refs.t2sInput as HTMLInputElement).click()">
              {{ newT2sFile ? newT2sFile.name : t.voiceModal.selectFile }}
            </button>
            <input ref="t2sInput" type="file" accept=".ckpt" hidden @change="onT2sPicked" />
          </div>
          <div class="um-file-row">
            <label class="um-file-label">{{ t.voiceModal.vitsLabel }}</label>
            <button class="btn btn-ghost btn-sm um-file-btn" @click="($refs.vitsInput as HTMLInputElement).click()">
              {{ newVitsFile ? newVitsFile.name : t.voiceModal.selectFile }}
            </button>
            <input ref="vitsInput" type="file" accept=".pth" hidden @change="onVitsPicked" />
          </div>
        </div>

        <div class="um-actions">
          <button
            class="btn btn-primary"
            :disabled="uploadStep === 'uploading' || !newName.trim() || !newT2sFile || !newVitsFile"
            @click="doUploadAndCreate"
          >
            {{ uploadStep === 'uploading' ? t.voiceModal.uploading : t.voiceModal.createAndLoad }}
          </button>
          <button class="btn btn-ghost" @click="showUploadModal = false">{{ t.voiceModal.cancel }}</button>
        </div>
      </div>
    </div>
    </Teleport>
  </div>
</template>

<style scoped>
.home {
  flex: 1;
  min-height: 0;
  width: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  scroll-behavior: smooth;
  background: var(--c-bg);
  position: relative;
}

/* ---- Hero ---- */
.hero {
  position: relative; z-index: 1;
  min-height: calc(100vh - 36px);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  text-align: center; max-width: 520px; margin: 0 auto; padding: 80px 32px;
}
.hero-logo { width: 80px; height: 80px; margin-bottom: 24px; filter: drop-shadow(0 0 24px var(--c-accent-glow)); }
.hero-badge {
  display: inline-block; padding: 5px 16px; border-radius: 100px;
  background: var(--c-accent-bg); color: var(--c-accent);
  font-size: 11px; font-weight: 600; letter-spacing: 0.08em;
  text-transform: uppercase; margin-bottom: 24px;
  border: 1px solid rgba(124, 252, 0, 0.15);
}
.hero-title {
  font-family: var(--font-display); font-size: 56px; font-weight: 700;
  line-height: 1.05; letter-spacing: -0.03em; color: var(--c-text); margin-bottom: 20px;
}
.hero-desc { font-size: 15px; line-height: 1.8; color: var(--c-text-secondary); margin-bottom: 32px; }
.hero-features { display: flex; align-items: center; justify-content: center; gap: 16px; margin-bottom: 40px; font-size: 13px; color: var(--c-text-secondary); }
.feature { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.feature-num { font-family: var(--font-display); font-size: 15px; font-weight: 600; color: var(--c-text); }
.feature-label { font-size: 11px; color: var(--c-text-muted); }
.feature-sep { color: var(--c-text-muted); }
.hero-cta { margin-bottom: 12px; transition: all 0.4s var(--ease-out); }
.hero-cta.hovering { transform: scale(1.04); }
.cta-icon { font-size: 18px; font-weight: 300; margin-right: 2px; }
.hero-nav { display: flex; gap: 12px; justify-content: center; }
.hero-version { font-size: 11px; color: var(--c-text-muted); opacity: 0.5; letter-spacing: 0.03em; margin-top: 24px; }
.hero-actions { display: flex; gap: 12px; align-items: center; justify-content: center; }
.trial-badge {
  font-size: 10px; font-weight: 600; padding: 3px 10px; border-radius: 100px;
  background: var(--c-accent-bg-2); color: var(--c-accent); white-space: nowrap;
}

/* ---- Scroll hint ---- */
.scroll-hint {
  position: absolute; bottom: 32px; left: 50%; transform: translateX(-50%);
  font-size: 12px; color: var(--c-text-muted);
  animation: bounce 2s ease-in-out infinite;
}
@keyframes bounce {
  0%, 100% { opacity: 0.3; transform: translateX(-50%) translateY(0); }
  50% { opacity: 1; transform: translateX(-50%) translateY(6px); }
}

/* ---- Dashboard ---- */
.dashboard {
  position: relative; z-index: 1;
}
.dash-main { padding: 48px 64px 80px; display: flex; flex-direction: column; gap: 48px; max-width: 960px; margin: 0 auto; }

.dash-section { }
.section-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.section-head h2 { font-family: var(--font-display); font-size: 18px; font-weight: 600; color: var(--c-text); }
.empty-state { text-align: center; color: var(--c-text-muted); padding: 40px 0; font-size: 13px; }

/* ---- Profile Cards ---- */
.profile-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 20px;
}
.profile-card {
  background: var(--c-bg-elevated);
  border: 1px solid var(--c-border);
  border-radius: var(--radius-lg);
  padding: 28px 16px 20px;
  cursor: pointer;
  transition: border-color 0.2s, transform 0.15s, box-shadow 0.2s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  text-align: center;
}
.profile-card:hover {
  border-color: var(--c-accent);
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(124, 252, 0, 0.06);
}

.pc-avatar {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  overflow: hidden;
  border: 2px solid var(--c-border);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(124, 252, 0, 0.06);
}
.pc-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.pc-avatar.placeholder {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 700;
  color: var(--c-accent);
  text-transform: uppercase;
}
.pc-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text);
  line-height: 1.3;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pc-desc {
  font-size: 11px;
  color: var(--c-text-muted);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Add card */
.add-card {
  border-style: dashed;
  border-color: var(--c-border);
  opacity: 0.6;
}
.add-card:hover {
  opacity: 1;
  border-color: var(--c-accent);
}
.add-avatar {
  font-size: 32px;
  font-weight: 300;
  color: var(--c-text-muted);
}
.add-card:hover .add-avatar {
  color: var(--c-accent);
}

/* ---- Upload Modal ---- */
.modal-overlay {
  position: fixed; inset: 0;
  background: var(--c-bg-overlay);
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
}
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
}
.upload-modal label {
  font-size: 12px;
  font-weight: 600;
  color: var(--c-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Avatar upload */
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

.um-input {
  width: 100%;
  font-family: inherit;
  font-size: 14px;
  padding: 10px 14px;
  background: var(--c-bg-input);
  border: 1px solid var(--c-border);
  border-radius: var(--radius-sm);
  color: var(--c-text);
}
.um-input:focus {
  border-color: var(--c-accent);
  outline: none;
}
.um-input::placeholder { color: var(--c-text-muted); }

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

/* ---- History ---- */
.history-list { display: flex; flex-direction: column; gap: 4px; }
.history-card {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px; border-radius: var(--radius-md); cursor: pointer;
  transition: background 0.15s;
}
.history-card:hover { background: var(--c-bg-glass); }
.hc-left { display: flex; flex-direction: column; gap: 4px; overflow: hidden; }
.hc-text { font-size: 14px; color: var(--c-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hc-meta { font-size: 11px; color: var(--c-text-muted); font-family: var(--font-mono); }
.hc-actions { display: flex; gap: 4px; flex-shrink: 0; }

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