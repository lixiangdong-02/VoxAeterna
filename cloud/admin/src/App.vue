<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAdminStore } from './stores/adminStore'

const store = useAdminStore()
const currentView = ref<'dashboard' | 'users' | 'announcements'>('dashboard')

const loginEmail = ref('admin@voxaeterna.local')
const loginPass = ref('')
const subModalUser = ref<number | null>(null)
const subModalPlan = ref('monthly')
const subModalDays = ref<number | null>(null)
const showAnnForm = ref(false)
const newAnn = ref({ title: '', body: '' })

const views = [
  { key: 'dashboard', label: '仪表盘' },
  { key: 'users', label: '用户管理' },
  { key: 'announcements', label: '公告管理' },
] as const

const pageTitle = computed(() => views.find(v => v.key === currentView.value)?.label || '')

const statsList = computed(() => [
  { label: '用户总数', value: store.stats.total_users },
  { label: '有效订阅', value: store.stats.active_subscriptions },
  { label: '合成次数', value: store.stats.total_synthesis_count },
  { label: '待付款订单', value: store.stats.pending_orders },
])

async function doLogin() {
  const ok = await store.login(loginEmail.value, loginPass.value)
  if (ok) store.fetchStats()
}

function onNavigate(key: string) {
  currentView.value = key as any
  if (key === 'dashboard') store.fetchStats()
  if (key === 'users') store.fetchUsers()
  if (key === 'announcements') store.fetchAnnouncements()
}

function openSubModal(userId: number) {
  subModalUser.value = userId
  subModalPlan.value = 'monthly'
  subModalDays.value = null
}

async function doCreateSub() {
  if (!subModalUser.value) return
  await store.createSubscription({
    user_id: subModalUser.value,
    plan: subModalPlan.value,
    duration_days: subModalDays.value || undefined,
  })
  subModalUser.value = null
}

async function createAnn() {
  await store.createAnnouncement(newAnn.value)
  newAnn.value = { title: '', body: '' }
  showAnnForm.value = false
}
</script>

<template>
  <!-- 登录页 -->
  <div v-if="!store.isLoggedIn" class="login-page">
    <div class="login-card">
      <div class="login-header">
        <h1>VoxAeterna</h1>
        <span>管理员登录</span>
      </div>
      <form class="login-form" @submit.prevent="doLogin()">
        <input v-model="loginEmail" type="email" placeholder="邮箱" />
        <input v-model="loginPass" type="password" placeholder="密码" />
        <button class="btn btn-primary" type="submit">登录</button>
        <p v-if="store.loginError" class="err">{{ store.loginError }}</p>
      </form>
    </div>
  </div>

  <!-- 管理后台 -->
  <div v-else class="admin-layout">
    <aside class="sidebar">
      <div class="sb-brand">
        <span class="sb-logo">VA</span>
        VoxAeterna
      </div>
      <nav class="sb-nav">
        <button
          v-for="v in views" :key="v.key"
          :class="{ active: currentView === v.key }"
          @click="onNavigate(v.key)"
        >{{ v.label }}</button>
      </nav>
      <button class="btn btn-ghost btn-sm sb-logout" @click="store.logout()">退出</button>
    </aside>

    <main class="main-content">
      <header class="topbar">
        <h2>{{ pageTitle }}</h2>
      </header>

      <!-- 仪表盘 -->
      <div v-if="currentView === 'dashboard'" class="dashboard">
        <div class="stat-card" v-for="s in statsList" :key="s.label">
          <span class="stat-num">{{ s.value }}</span>
          <span class="stat-label">{{ s.label }}</span>
        </div>
      </div>

      <!-- 用户管理 -->
      <div v-if="currentView === 'users'" class="users-view">
        <div class="toolbar">
          <input v-model="store.searchQuery" placeholder="搜索邮箱或用户名…" @keyup.enter="store.fetchUsers(1, store.searchQuery)" />
          <button class="btn btn-primary btn-sm" @click="store.fetchUsers(1, store.searchQuery)">搜索</button>
        </div>
        <table class="data-table">
          <thead>
            <tr>
              <th>ID</th><th>邮箱</th><th>用户名</th><th>角色</th><th>状态</th><th>订阅</th><th>试用剩余</th><th>注册时间</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in store.users" :key="u.id">
              <td>{{ u.id }}</td>
              <td>{{ u.email }}</td>
              <td>{{ u.username }}</td>
              <td>{{ u.role }}</td>
              <td><span class="badge" :class="u.status">{{ u.status }}</span></td>
              <td>{{ u.subscription_plan || '—' }} / {{ u.subscription_status || '—' }}</td>
              <td>{{ u.trial_remaining ?? '—' }}</td>
              <td class="date-cell">{{ u.created_at?.split('T')[0] || '—' }}</td>
              <td class="action-cell">
                <button v-if="u.status !== 'banned'" class="btn btn-ghost btn-sm" @click="store.updateUser(u.id, { status: 'banned' })">封禁</button>
                <button v-if="u.status !== 'active'" class="btn btn-ghost btn-sm" @click="store.updateUser(u.id, { status: 'active' })">解封</button>
                <button class="btn btn-ghost btn-sm" @click="openSubModal(u.id)">开通订阅</button>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="pagination">
          <span>共 {{ store.usersTotal }} 条</span>
          <button :disabled="store.usersPage <= 1" @click="store.fetchUsers(store.usersPage - 1)">上一页</button>
          <button :disabled="store.users.length < 20" @click="store.fetchUsers(store.usersPage + 1)">下一页</button>
        </div>
      </div>

      <!-- 公告管理 -->
      <div v-if="currentView === 'announcements'" class="announcements-view">
        <div class="toolbar">
          <button class="btn btn-primary btn-sm" @click="showAnnForm = true">新建公告</button>
        </div>
        <div v-if="showAnnForm" class="ann-form">
          <input v-model="newAnn.title" placeholder="标题" />
          <textarea v-model="newAnn.body" rows="4" placeholder="内容"></textarea>
          <div class="form-actions">
            <button class="btn btn-primary btn-sm" @click="createAnn()">发布</button>
            <button class="btn btn-ghost btn-sm" @click="showAnnForm = false">取消</button>
          </div>
        </div>
        <div v-for="a in store.announcements" :key="a.id" class="ann-item">
          <div class="ann-head">
            <strong>{{ a.title }}</strong>
            <span class="badge" :class="{ active: a.is_active }">{{ a.is_active ? '显示中' : '已隐藏' }}</span>
          </div>
          <p class="ann-body">{{ a.body }}</p>
          <div class="ann-meta">
            <span>{{ a.created_at?.split('T')[0] || '' }}</span>
            <button class="btn btn-ghost btn-sm" @click="store.updateAnnouncement(a.id, { is_active: !a.is_active })">
              {{ a.is_active ? '隐藏' : '显示' }}
            </button>
          </div>
        </div>
      </div>
    </main>

    <!-- 开通订阅弹窗 -->
    <div v-if="subModalUser !== null" class="modal-overlay" @click.self="subModalUser = null">
      <div class="modal">
        <h3>开通订阅</h3>
        <p>用户 ID: {{ subModalUser }}</p>
        <select v-model="subModalPlan">
          <option value="monthly">月租 ¥19.9</option>
          <option value="yearly">年租 ¥219</option>
          <option value="lifetime">买断 ¥699</option>
        </select>
        <input v-model.number="subModalDays" type="number" placeholder="天数（留空用默认）" />
        <div class="form-actions">
          <button class="btn btn-primary btn-sm" @click="doCreateSub()">确认</button>
          <button class="btn btn-ghost btn-sm" @click="subModalUser = null">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
:root {
  --c-accent: #7CFC00;
  --c-accent-glow: rgba(124, 252, 0, 0.25);
  --c-bg: #0D0D0C;
  --c-bg-elevated: #161614;
  --c-bg-glass: rgba(255,255,255,0.03);
  --c-text: #EBEBE8;
  --c-text-secondary: #9D9D98;
  --c-text-muted: #5E5E5A;
  --c-border: rgba(255,255,255,0.06);
  --c-danger: #E0523D;
  --radius-sm: 6px; --radius-md: 10px;
  --font-body: 'Microsoft YaHei', 'PingFang SC', sans-serif;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: var(--font-body); font-size: 13px; color: var(--c-text); background: var(--c-bg); }
.btn { display:inline-flex; align-items:center; gap:4px; padding:6px 14px; border:none; border-radius:var(--radius-sm); font-size:12px; cursor:pointer; font-family:inherit; }
.btn-primary { background:var(--c-accent); color:#0A0A08; }
.btn-primary:hover { filter: brightness(1.1); }
.btn-ghost { background:transparent; color:var(--c-text-secondary); }
.btn-ghost:hover { background:var(--c-bg-glass); color:var(--c-text); }
.btn-sm { padding:4px 10px; font-size:11px; }
input, textarea, select { font-family:inherit; font-size:13px; background:rgba(255,255,255,0.04); border:1px solid var(--c-border); border-radius:var(--radius-sm); padding:8px 12px; color:var(--c-text); }
input:focus, textarea:focus, select:focus { border-color:var(--c-accent); outline:none; }
::-webkit-scrollbar { width:4px; } ::-webkit-scrollbar-thumb { background:rgba(255,255,255,0.08); border-radius:2px; }

.login-page { height:100vh; display:flex; align-items:center; justify-content:center; background: var(--c-bg); }
.login-card { width:360px; padding:40px; border:1px solid var(--c-border); border-radius:var(--radius-md); background:var(--c-bg-elevated); }
.login-header { text-align:center; margin-bottom:24px; }
.login-header h1 { font-size:24px; letter-spacing:-0.02em; }
.login-header span { font-size:12px; color:var(--c-text-muted); }
.login-form { display:flex; flex-direction:column; gap:12px; }
.login-form input { width:100%; }
.login-form .btn { width:100%; justify-content:center; padding:10px; }
.err { font-size:11px; color:var(--c-danger); text-align:center; }

.admin-layout { display:flex; height:100vh; }
.sidebar { width:200px; background:var(--c-bg-elevated); border-right:1px solid var(--c-border); display:flex; flex-direction:column; padding:20px 12px; flex-shrink:0; }
.sb-brand { display:flex; align-items:center; gap:8px; font-size:15px; font-weight:700; margin-bottom:24px; }
.sb-logo { background:var(--c-accent); color:#0A0A08; width:28px; height:28px; border-radius:6px; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:800; }
.sb-nav { display:flex; flex-direction:column; gap:4px; flex:1; }
.sb-nav button { background:transparent; border:none; color:var(--c-text-secondary); font-size:13px; padding:8px 12px; border-radius:var(--radius-sm); cursor:pointer; text-align:left; }
.sb-nav button:hover { background:var(--c-bg-glass); }
.sb-nav button.active { background:rgba(124,252,0,0.08); color:var(--c-accent); }
.sb-logout { margin-top:auto; width:100%; justify-content:center; }

.main-content { flex:1; overflow-y:auto; padding:24px; display:flex; flex-direction:column; gap:20px; }
.topbar h2 { font-size:18px; font-weight:600; letter-spacing:-0.01em; }

.dashboard { display:grid; grid-template-columns:repeat(4,1fr); gap:16px; }
.stat-card { background:var(--c-bg-elevated); border:1px solid var(--c-border); border-radius:var(--radius-md); padding:24px; display:flex; flex-direction:column; gap:6px; }
.stat-num { font-size:32px; font-weight:700; color:var(--c-accent); }
.stat-label { font-size:12px; color:var(--c-text-muted); text-transform:uppercase; letter-spacing:0.04em; }

.toolbar { display:flex; gap:8px; align-items:center; margin-bottom:16px; }
.data-table { width:100%; border-collapse:collapse; }
.data-table th, .data-table td { text-align:left; padding:10px 12px; border-bottom:1px solid var(--c-border); font-size:12px; }
.data-table th { color:var(--c-text-muted); font-weight:600; text-transform:uppercase; letter-spacing:0.04em; font-size:10px; }
.badge { font-size:10px; padding:2px 8px; border-radius:100px; font-weight:600; }
.badge.active { background:rgba(124,252,0,0.12); color:var(--c-accent); }
.badge.banned { background:rgba(224,82,61,0.12); color:var(--c-danger); }
.badge.disabled { background:rgba(157,157,152,0.12); color:var(--c-text-secondary); }
.date-cell { color:var(--c-text-muted); white-space:nowrap; }
.action-cell { display:flex; gap:4px; }
.pagination { display:flex; align-items:center; gap:12px; margin-top:12px; font-size:12px; color:var(--c-text-muted); }
.pagination button { padding:4px 12px; background:var(--c-bg-glass); border:1px solid var(--c-border); border-radius:4px; color:var(--c-text); cursor:pointer; font-size:11px; }
.pagination button:disabled { opacity:0.4; cursor:default; }

.ann-form { background:var(--c-bg-elevated); border:1px solid var(--c-border); border-radius:var(--radius-md); padding:16px; display:flex; flex-direction:column; gap:12px; }
.form-actions { display:flex; gap:8px; }
.ann-item { background:var(--c-bg-elevated); border:1px solid var(--c-border); border-radius:var(--radius-md); padding:16px; display:flex; flex-direction:column; gap:8px; }
.ann-head { display:flex; justify-content:space-between; align-items:center; }
.ann-body { font-size:13px; color:var(--c-text-secondary); line-height:1.6; }
.ann-meta { display:flex; justify-content:space-between; align-items:center; font-size:11px; color:var(--c-text-muted); }

.modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.6); display:flex; align-items:center; justify-content:center; z-index:100; }
.modal { background:var(--c-bg-elevated); border:1px solid var(--c-border); border-radius:var(--radius-md); padding:24px; width:360px; display:flex; flex-direction:column; gap:14px; }
.modal h3 { font-size:16px; }
</style>
