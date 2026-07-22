<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'
import { useUserStore } from '@/stores/userStore'
import { useLocaleStore } from '@/stores/localeStore'
import { authApi, cloudApi } from '@/api'
import type { SubscriptionStatus, UsageStats, PaymentRecord } from '@/types'
import UpgradeModal from '@/components/UpgradeModal.vue'

const router = useRouter()
const authStore = useAuthStore()
const userStore = useUserStore()
const localeStore = useLocaleStore()
const t = computed(() => localeStore.t)
const et = computed(() => localeStore.t.errors)
const _ = localeStore._

// ======= Data fetching =======
const sub = ref<SubscriptionStatus | null>(null)
const stats = ref<UsageStats | null>(null)
const payments = ref<PaymentRecord[]>([])
const sessions = ref<{ id: number; device_fingerprint: string; created_at: string | null }[]>([])

onMounted(async () => {
  try {
    const [subRes, statsRes, payRes, sessRes] = await Promise.allSettled([
      cloudApi.subscriptionStatus(),
      cloudApi.getUsageStats(),
      cloudApi.getPaymentHistory(),
      cloudApi.listSessions(),
    ])
    if (subRes.status === 'fulfilled') sub.value = subRes.value.data
    if (statsRes.status === 'fulfilled') stats.value = statsRes.value.data
    if (payRes.status === 'fulfilled') payments.value = (payRes.value.data.items || []).slice(0, 10)
    if (sessRes.status === 'fulfilled') sessions.value = sessRes.value.data.items || []
  } catch { /* silently degrade */ }
})

// ======= Username editing =======
const saving = ref(false)
const saveMsg = ref('')
const saveErr = ref('')
const editingName = ref(false)
const newName = ref('')

function startEditName() {
  newName.value = authStore.user?.username || ''
  editingName.value = true
}
async function saveName() {
  if (!newName.value.trim() || newName.value.trim().length < 2) {
    saveErr.value = et.value.usernameMin
    return
  }
  saving.value = true; saveErr.value = ''; saveMsg.value = ''
  try {
    const res = await authApi.updateProfile(newName.value.trim())
    if (authStore.user) authStore.user.username = res.data.username
    editingName.value = false
    saveMsg.value = t.value.profile.usernameUpdated
  } catch (e: any) {
    saveErr.value = e.response?.data?.detail || et.value.updateFailed
  } finally { saving.value = false }
}
function cancelEdit() { editingName.value = false; saveErr.value = '' }

// ======= Change password =======
const pwForm = reactive({ old: '', p1: '', p2: '' })
const pwMsg = ref(''); const pwErr = ref('')
const changingPw = ref(false)
const showPw = ref(false)

async function doChangePassword() {
  pwErr.value = ''; pwMsg.value = ''
  if (!pwForm.old) { pwErr.value = et.value.pwRequired; return }
  if (pwForm.p1.length < 6) { pwErr.value = et.value.pwMinLength; return }
  if (pwForm.p1 !== pwForm.p2) { pwErr.value = et.value.pwMismatch; return }
  changingPw.value = true
  try {
    await authApi.changePassword(pwForm.old, pwForm.p1)
    pwMsg.value = t.value.profile.pwChanged
    pwForm.old = ''; pwForm.p1 = ''; pwForm.p2 = ''
  } catch (e: any) {
    pwErr.value = e.response?.data?.detail || et.value.pwChangeFailed
  } finally { changingPw.value = false }
}

// ======= Revoke sessions =======
const revokingSessions = ref(false)
async function doRevokeSessions() {
  if (!confirm(t.value.profile.revokeAllConfirm)) return
  revokingSessions.value = true
  try {
    await cloudApi.revokeAllSessions()
    sessions.value = []
    alert(t.value.profile.revokeAllSuccess)
  } catch { /* ignore */ }
  finally { revokingSessions.value = false }
}

// ======= Delete account =======
const showDeleteConfirm = ref(false)
const deletePassword = ref('')
const deletingAccount = ref(false)
const deleteErr = ref('')

async function doDeleteAccount() {
  if (!deletePassword.value) { deleteErr.value = et.value.pwRequired; return }
  deletingAccount.value = true; deleteErr.value = ''
  try {
    await cloudApi.deleteAccount(deletePassword.value)
    alert(t.value.profile.deleteAccountSuccess)
    authStore.logout()
    router.push('/')
  } catch (e: any) {
    deleteErr.value = e.response?.data?.detail || et.value.updateFailed
  } finally { deletingAccount.value = false }
}

// ======= Upgrade modal =======
const showUpgrade = ref(false)

// ======= Helpers =======
function formatDuration(s: number): string {
  if (s < 60) return `${s.toFixed(0)}s`
  if (s < 3600) return `${(s / 60).toFixed(1)}m`
  return `${(s / 3600).toFixed(1)}h`
}

function planLabel(p: string): string {
  const map: Record<string, string> = { free: t.value.profile.planFree, monthly: t.value.profile.planMonthly, yearly: t.value.profile.planYearly, lifetime: t.value.profile.planLifetime }
  return map[p] || p
}

function statusLabel(s: string): string {
  const map: Record<string, string> = { pending: t.value.profile.statusPending, paid: t.value.profile.statusPaid, cancelled: t.value.profile.statusCancelled, refunded: t.value.profile.statusRefunded }
  return map[s] || s
}

function goBack() { router.push('/') }

function getUserInitial(): string {
  return (authStore.user?.username?.[0] || authStore.user?.email?.[0] || '?').toUpperCase()
}
</script>

<template>
  <div class="profile-page">
    <div class="profile-container">
      <header class="profile-header">
        <button class="btn btn-ghost btn-sm" @click="goBack">{{ t.profile.back }}</button>
        <h1>{{ t.profile.title }}</h1>
      </header>

      <div class="profile-grid">
        <!-- ====== SECTION 1: Basic Info ====== -->
        <section class="card">
          <div class="card-header">
            <h2>{{ t.profile.basicInfo }}</h2>
            <button v-if="!editingName" class="btn btn-ghost btn-xs" @click="startEditName">{{ t.profile.edit }}</button>
          </div>

          <div class="avatar-row">
            <div class="avatar-circle">{{ getUserInitial() }}</div>
            <div class="avatar-info">
              <div class="avatar-name">{{ authStore.user?.username }}</div>
              <div class="avatar-email">{{ authStore.user?.email }}</div>
              <div class="avatar-tags">
                <span v-if="authStore.user?.role === 'admin'" class="tag tag-admin">{{ t.profile.roleAdmin }}</span>
                <span v-if="authStore.user?.status === 'pending'" class="tag tag-warn">{{ t.profile.unverified }}</span>
              </div>
            </div>
          </div>

          <div v-if="editingName" class="edit-name-row">
            <input v-model="newName" class="input" maxlength="100" @keyup.enter="saveName" @keyup.escape="cancelEdit" />
            <button class="btn btn-primary btn-sm" :disabled="saving" @click="saveName">{{ t.profile.save }}</button>
            <button class="btn btn-ghost btn-sm" @click="cancelEdit">{{ t.profile.cancel }}</button>
          </div>

          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">{{ t.profile.email }}</span>
              <span class="info-value">{{ authStore.user?.email }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">{{ t.profile.createdAt }}</span>
              <span class="info-value">{{ authStore.user?.created_at?.split('T')[0] || '-' }}</span>
            </div>
          </div>

          <p v-if="saveMsg" class="msg-ok">{{ saveMsg }}</p>
          <p v-if="saveErr" class="msg-err">{{ saveErr }}</p>
        </section>

        <!-- ====== SECTION 2: Subscription ====== -->
        <section class="card">
          <div class="card-header">
            <h2>{{ t.profile.subscription }}</h2>
            <button v-if="sub?.plan === 'free'" class="btn btn-primary btn-xs" @click="showUpgrade = true">{{ t.profile.upgradeBtn }}</button>
            <span v-else class="badge badge-active">{{ t.profile.manageBtn }}</span>
          </div>

          <div class="plan-display">
            <div class="plan-big-name">{{ planLabel(sub?.plan || 'free') }}</div>
            <div v-if="sub?.plan !== 'free' && sub?.expires_at" class="plan-expiry">
              <div class="plan-expiry-label">{{ t.profile.expiresAt }}</div>
              <div class="plan-expiry-date">{{ sub.expires_at.split('T')[0] }}</div>
            </div>
            <div v-if="sub?.plan === 'free'" class="trial-row">
              <div class="trial-num">{{ sub?.trial_remaining ?? '…' }}</div>
              <div class="trial-label">{{ t.profile.trialRemaining }}</div>
            </div>
          </div>
        </section>

        <!-- ====== SECTION 3: Usage Stats ====== -->
        <section class="card">
          <h2>{{ t.profile.usageStats }}</h2>
          <div class="stats-grid">
            <div class="stat-block">
              <div class="stat-num">{{ stats?.total_syntheses ?? '…' }}</div>
              <div class="stat-label">{{ t.profile.totalSyntheses }}</div>
            </div>
            <div class="stat-block">
              <div class="stat-num">{{ stats ? formatDuration(stats.total_duration) : '…' }}</div>
              <div class="stat-label">{{ t.profile.totalDuration }}</div>
            </div>
            <div class="stat-block">
              <div class="stat-num">{{ stats?.month_syntheses ?? '…' }}</div>
              <div class="stat-label">{{ t.profile.monthSyntheses }}</div>
            </div>
            <div class="stat-block">
              <div class="stat-num">{{ stats ? formatDuration(stats.month_duration) : '…' }}</div>
              <div class="stat-label">{{ t.profile.monthDuration }}</div>
            </div>
          </div>
          <div v-if="stats" class="account-age">
            {{ t.profile.accountAge }}: {{ _('profile.accountAgeDays', { n: stats.account_age_days }) }}
          </div>
        </section>

        <!-- ====== Payment History ====== -->
        <section class="card" v-if="payments.length > 0">
          <h2>{{ t.profile.paymentHistory }}</h2>
          <div class="pay-list">
            <div v-for="p in payments" :key="p.id" class="pay-item">
              <div class="pay-left">
                <span class="pay-plan">{{ planLabel(p.plan) }}</span>
                <span class="pay-time">{{ p.created_at?.split('T')[0] || '-' }}</span>
              </div>
              <div class="pay-right">
                <span class="pay-amount">¥{{ p.amount.toFixed(2) }}</span>
                <span class="pay-status" :class="'pay-' + p.status">{{ statusLabel(p.status) }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- ====== SECTION 4: Security ====== -->
        <section class="card">
          <h2>{{ t.profile.security }}</h2>

          <!-- Change Password -->
          <div class="security-block">
            <div class="security-header" @click="showPw = !showPw">
              <span>{{ t.profile.changePassword }}</span>
              <span class="toggle-icon">{{ showPw ? '▾' : '▸' }}</span>
            </div>
            <div v-if="showPw" class="security-body">
              <div class="form-group">
                <label>{{ t.profile.oldPassword }}</label>
                <input v-model="pwForm.old" type="password" class="input" :placeholder="t.profile.oldPasswordPlaceholder" />
              </div>
              <div class="form-group">
                <label>{{ t.profile.newPassword }}</label>
                <input v-model="pwForm.p1" type="password" class="input" :placeholder="t.profile.newPasswordPlaceholder" />
              </div>
              <div class="form-group">
                <label>{{ t.profile.confirmPassword }}</label>
                <input v-model="pwForm.p2" type="password" class="input" :placeholder="t.profile.confirmPasswordPlaceholder" />
              </div>
              <button class="btn btn-primary btn-sm" :disabled="changingPw" @click="doChangePassword">
                {{ changingPw ? t.profile.changingPw : t.profile.changePwBtn }}
              </button>
              <p v-if="pwMsg" class="msg-ok">{{ pwMsg }}</p>
              <p v-if="pwErr" class="msg-err">{{ pwErr }}</p>
            </div>
          </div>

          <!-- Sessions -->
          <div class="security-block" v-if="sessions.length > 0">
            <div class="security-header">
              <span>{{ t.profile.activeSessions }} ({{ sessions.length }})</span>
            </div>
            <div class="session-list">
              <div v-for="s in sessions.slice(0, 5)" :key="s.id" class="session-item">
                <span class="session-device">{{ s.device_fingerprint?.slice(0, 16) || '…' }}</span>
                <span class="session-time">{{ s.created_at?.split('T')[0] || '-' }}</span>
              </div>
            </div>
            <button class="btn btn-ghost btn-sm revoke-btn" :disabled="revokingSessions" @click="doRevokeSessions">
              {{ t.profile.revokeAllSessions }}
            </button>
          </div>
        </section>

        <!-- ====== Delete Account ====== -->
        <section class="card card-danger">
          <h2>{{ t.profile.deleteAccount }}</h2>
          <p class="danger-text">{{ t.profile.deleteAccountWarn }}</p>
          <div v-if="showDeleteConfirm" class="delete-form">
            <input v-model="deletePassword" type="password" class="input" :placeholder="t.profile.deleteAccountConfirm" />
            <button class="btn btn-danger btn-sm" :disabled="deletingAccount" @click="doDeleteAccount">
              {{ t.profile.deleteAccountBtn }}
            </button>
            <button class="btn btn-ghost btn-sm" @click="showDeleteConfirm = false; deletePassword = ''; deleteErr = ''">{{ t.profile.cancel }}</button>
            <p v-if="deleteErr" class="msg-err">{{ deleteErr }}</p>
          </div>
          <button v-else class="btn btn-danger btn-xs" @click="showDeleteConfirm = true">{{ t.profile.deleteAccount }}</button>
        </section>
      </div>
    </div>
  </div>

  <!-- Upgrade Modal -->
  <UpgradeModal v-if="showUpgrade" @close="showUpgrade = false; userStore.fetchStatus().then(() => cloudApi.subscriptionStatus().then(r => sub = r.data))" />
</template>

<style scoped>
.profile-page {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  background: var(--c-bg);
  overflow-y: auto;
  padding: 32px 16px;
}

.profile-container {
  width: 680px;
  max-width: 90vw;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 16px;
}
.profile-header h1 {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
  color: var(--c-text);
}

.profile-grid {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ---- Cards ---- */
.card {
  background: var(--c-bg-elevated);
  border: 1px solid var(--c-border);
  border-radius: var(--radius-md);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.card h2 {
  font-size: 13px;
  font-weight: 600;
  color: var(--c-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin: 0;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-danger {
  border-color: var(--c-danger-border);
  background: var(--c-danger-bg);
}

/* ---- Avatar ---- */
.avatar-row { display: flex; align-items: center; gap: 16px; }
.avatar-circle {
  width: 56px; height: 56px;
  border-radius: 50%;
  background: var(--c-accent);
  color: var(--c-btn-primary-text);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 700;
  font-family: var(--font-display);
  flex-shrink: 0;
}
.avatar-name { font-size: 16px; font-weight: 600; color: var(--c-text); }
.avatar-email { font-size: 13px; color: var(--c-text-muted); }
.avatar-tags { display: flex; gap: 6px; margin-top: 4px; }
.tag { font-size: 10px; padding: 1px 6px; border-radius: 100px; font-weight: 600; }
.tag-admin { background: var(--c-amber-bg); color: var(--c-amber); }
.tag-warn { background: var(--c-danger-bg); color: var(--c-danger); }

.edit-name-row { display: flex; gap: 8px; align-items: center; }
.edit-name-row .input { flex: 1; }

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.info-item { display: flex; flex-direction: column; gap: 2px; }
.info-label { font-size: 11px; color: var(--c-text-muted); text-transform: uppercase; letter-spacing: 0.04em; }
.info-value { font-size: 13px; color: var(--c-text); }

/* ---- Plan display ---- */
.plan-display { padding: 8px 0; }
.plan-big-name { font-size: 24px; font-weight: 700; color: var(--c-accent); font-family: var(--font-display); }
.plan-expiry { display: flex; gap: 8px; align-items: baseline; margin-top: 4px; }
.plan-expiry-label { font-size: 12px; color: var(--c-text-muted); }
.plan-expiry-date { font-size: 13px; color: var(--c-text); font-weight: 500; }
.trial-row { display: flex; gap: 12px; align-items: baseline; margin-top: 4px; }
.trial-num { font-size: 32px; font-weight: 700; color: var(--c-text); font-family: var(--font-display); }
.trial-label { font-size: 13px; color: var(--c-text-muted); }
.badge-active { font-size: 10px; padding: 2px 8px; border-radius: 100px; background: var(--c-accent-bg); color: var(--c-accent); }

/* ---- Stats ---- */
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.stat-block { text-align: center; padding: 12px 8px; background: var(--c-bg); border-radius: var(--radius-sm); }
.stat-num { font-size: 22px; font-weight: 700; color: var(--c-text); font-family: var(--font-display); }
.stat-label { font-size: 10px; color: var(--c-text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-top: 4px; }
.account-age { font-size: 12px; color: var(--c-text-muted); text-align: center; }

/* ---- Payment history ---- */
.pay-list { display: flex; flex-direction: column; gap: 2px; }
.pay-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--c-border); }
.pay-item:last-child { border-bottom: none; }
.pay-left { display: flex; flex-direction: column; gap: 2px; }
.pay-plan { font-size: 13px; font-weight: 500; color: var(--c-text); }
.pay-time { font-size: 11px; color: var(--c-text-muted); }
.pay-right { display: flex; align-items: center; gap: 10px; }
.pay-amount { font-size: 14px; font-weight: 600; color: var(--c-text); font-family: var(--font-mono); }
.pay-status { font-size: 11px; padding: 2px 6px; border-radius: 100px; }
.pay-pending { background: var(--c-amber-bg); color: var(--c-amber); }
.pay-paid { background: var(--c-accent-bg); color: var(--c-accent); }
.pay-cancelled { background: var(--c-bg-glass); color: var(--c-text-muted); }
.pay-refunded { background: var(--c-danger-bg); color: var(--c-danger); }

/* ---- Security ---- */
.security-block { border-top: 1px solid var(--c-border); padding-top: 12px; }
.security-block:first-child { border-top: none; padding-top: 0; }
.security-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  color: var(--c-text);
  cursor: pointer;
  padding: 4px 0;
}
.security-header:hover { color: var(--c-accent); }
.toggle-icon { font-size: 12px; color: var(--c-text-muted); }
.security-body {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.form-group { display: flex; flex-direction: column; gap: 4px; }
.form-group label { font-size: 12px; color: var(--c-text-secondary); }
.input {
  padding: 8px 12px;
  border: 1px solid var(--c-border);
  border-radius: var(--radius-sm);
  background: var(--c-bg-input);
  color: var(--c-text);
  font-size: 14px;
  font-family: inherit;
  outline: none;
}
.input:focus { border-color: var(--c-accent); }
.input::placeholder { color: var(--c-text-muted); }

.session-list { padding: 4px 0; }
.session-item { display: flex; justify-content: space-between; padding: 4px 0; font-size: 12px; }
.session-device { color: var(--c-text); font-family: var(--font-mono); }
.session-time { color: var(--c-text-muted); }
.revoke-btn { margin-top: 8px; }

/* ---- Danger zone ---- */
.danger-text { font-size: 13px; color: var(--c-danger); margin-top: -8px; }
.delete-form { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }

/* ---- Utilities ---- */
.msg-ok { font-size: 13px; color: var(--c-accent); margin: 0; }
.msg-err { font-size: 13px; color: var(--c-danger); margin: 0; }
.btn-xs { font-size: 11px; padding: 3px 10px; }
.btn-sm { font-size: 12px; padding: 5px 14px; }
.btn-danger {
  background: var(--c-danger);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-family: inherit;
}
.btn-danger:hover { opacity: 0.85; }
.btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }

@media (max-width: 600px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .info-grid { grid-template-columns: 1fr; }
}
</style>
