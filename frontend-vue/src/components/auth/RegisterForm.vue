<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const username = ref('')
const email = ref('')
const password = ref('')
const error = ref<string | null>(null)
const success = ref(false)
const isLoading = ref(false)

async function handleSubmit(): Promise<void> {
  error.value = null
  success.value = false
  isLoading.value = true
  try {
    await authStore.register({ username: username.value, email: email.value, password: password.value })
    success.value = true
    username.value = ''
    email.value = ''
    password.value = ''
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Registration failed. Please try again.'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <form class="space-y-4" @submit.prevent="handleSubmit">
    <div class="space-y-2">
      <label for="reg-username" class="block text-sm font-medium text-foreground">Username</label>
      <input
        id="reg-username"
        v-model="username"
        type="text"
        autocomplete="username"
        required
        :disabled="isLoading"
        class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50"
        placeholder="Choose a username"
      />
    </div>

    <div class="space-y-2">
      <label for="reg-email" class="block text-sm font-medium text-foreground">Email</label>
      <input
        id="reg-email"
        v-model="email"
        type="email"
        autocomplete="email"
        required
        :disabled="isLoading"
        class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50"
        placeholder="Enter your email"
      />
    </div>

    <div class="space-y-2">
      <label for="reg-password" class="block text-sm font-medium text-foreground">Password</label>
      <input
        id="reg-password"
        v-model="password"
        type="password"
        autocomplete="new-password"
        required
        :disabled="isLoading"
        class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50"
        placeholder="Create a password"
      />
    </div>

    <p v-if="error" role="alert" class="text-sm text-destructive">{{ error }}</p>

    <p v-if="success" class="text-sm text-green-600 dark:text-green-400">
      Account created! You can now sign in. Account registered successfully.
    </p>

    <button
      type="submit"
      :disabled="isLoading || !username || !email || !password"
      class="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 transition-colors"
    >
      {{ isLoading ? 'Creating account…' : 'Create account' }}
    </button>
  </form>
</template>
