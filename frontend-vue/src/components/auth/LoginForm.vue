<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const error = ref<string | null>(null)
const isLoading = ref(false)

async function handleSubmit(): Promise<void> {
  error.value = null
  isLoading.value = true
  try {
    await authStore.login({ username: username.value, password: password.value })
    await router.push('/chat')
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Login failed. Please check your credentials.'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <form class="space-y-4" @submit.prevent="handleSubmit">
    <div class="space-y-2">
      <label for="login-username" class="block text-sm font-medium text-foreground">
        Username
      </label>
      <input
        id="login-username"
        v-model="username"
        type="text"
        autocomplete="username"
        required
        :disabled="isLoading"
        aria-describedby="login-error"
        class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        placeholder="Enter your username"
      />
    </div>

    <div class="space-y-2">
      <label for="login-password" class="block text-sm font-medium text-foreground">
        Password
      </label>
      <input
        id="login-password"
        v-model="password"
        type="password"
        autocomplete="current-password"
        required
        :disabled="isLoading"
        class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        placeholder="Enter your password"
      />
    </div>

    <p
      v-if="error"
      id="login-error"
      role="alert"
      class="text-sm text-destructive"
    >
      {{ error }}
    </p>

    <button
      type="submit"
      :disabled="isLoading || !username || !password"
      class="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
    >
      {{ isLoading ? 'Signing in…' : 'Sign in' }}
    </button>
  </form>
</template>
