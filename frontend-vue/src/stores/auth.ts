import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import * as authApi from '@/api/auth'
import type { User } from '@/api/types'
import type { LoginCredentials, RegisterCredentials } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => user.value !== null)

  async function login(credentials: LoginCredentials): Promise<void> {
    isLoading.value = true
    error.value = null
    try {
      const data = await authApi.loginJson(credentials)
      user.value = { id: data.user_id, username: data.username, email: '' }
    } finally {
      isLoading.value = false
    }
  }

  async function register(credentials: RegisterCredentials): Promise<void> {
    isLoading.value = true
    error.value = null
    try {
      await authApi.register(credentials)
    } finally {
      isLoading.value = false
    }
  }

  async function logout(): Promise<void> {
    try {
      await authApi.logout()
    } finally {
      clear()
    }
  }

  async function fetchCurrentUser(): Promise<void> {
    try {
      user.value = await authApi.getMe()
    } catch {
      user.value = null
    }
  }

  // clear() replaces $reset() — setup stores don't have $reset() built-in
  function clear(): void {
    user.value = null
    error.value = null
    isLoading.value = false
  }

  return {
    user,
    isLoading,
    error,
    isAuthenticated,
    login,
    register,
    logout,
    fetchCurrentUser,
    clear,
  }
})
