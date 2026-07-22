/** Vue Router —— Home → Login/Register → Workspace */
import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('../views/HomePage.vue'),
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginPage.vue'),
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/RegisterPage.vue'),
    },
    {
      path: '/forgot-password',
      name: 'forgot-password',
      component: () => import('../views/ForgotPasswordPage.vue'),
    },
    {
      path: '/workspace',
      name: 'workspace',
      component: () => import('../views/WorkspaceView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('../views/ProfilePage.vue'),
      meta: { requiresAuth: true },
    },
  ],
})

// 路由守卫：未登录不能进 workspace
router.beforeEach(async (to, _from, next) => {
  if (to.meta.requiresAuth) {
    const token = localStorage.getItem('vox_token')
    if (!token) {
      next('/login')
      return
    }
    // 验证 token 有效
    try {
      const { useAuthStore } = await import('@/stores/authStore')
      const authStore = useAuthStore()
      if (!authStore.isLoggedIn) {
        const ok = await authStore.restoreSession()
        if (!ok) {
          next('/login')
          return
        }
      }
    } catch {
      next('/login')
      return
    }
  }
  next()
})

export default router
