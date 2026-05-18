import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import type { User } from '@/api/types'
import type { Ref, ComputedRef } from 'vue'

export interface UseAuthReturn {
  user: Ref<User | null>
  isAuthenticated: ComputedRef<boolean>
  isLoading: Ref<boolean>
  login: (credentials: { username: string; password: string }) => Promise<void>
  logout: () => Promise<void>
  register: (credentials: { username: string; email: string; password: string }) => Promise<void>
  fetchCurrentUser: () => Promise<void>
  clear: () => void
}

export function useAuth(): UseAuthReturn {
  const authStore = useAuthStore()
  const { user, isAuthenticated, isLoading } = storeToRefs(authStore)
  const { login, logout, register, fetchCurrentUser, clear } = authStore

  return { user, isAuthenticated, isLoading, login, logout, register, fetchCurrentUser, clear }
}
