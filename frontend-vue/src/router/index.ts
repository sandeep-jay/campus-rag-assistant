import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

export const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
  },
  {
    path: '/chat/:sessionId?',
    name: 'chat',
    component: () => import('@/views/ChatView.vue'),
    meta: { requiresAuth: true },
  },
  {
    // Catch-all: redirect unknown paths to login
    path: '/:pathMatch(.*)*',
    redirect: '/login',
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

// Modern Vue Router 4 guard — return a route to redirect, or undefined to continue
router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (to.meta.requiresAuth) {
    // If no user in store, try to hydrate from cookie
    if (!auth.isAuthenticated) {
      await auth.fetchCurrentUser()
    }
    // If still not authenticated after hydration attempt, redirect to login
    if (!auth.isAuthenticated) {
      return '/login'
    }
  }
})

export default router
