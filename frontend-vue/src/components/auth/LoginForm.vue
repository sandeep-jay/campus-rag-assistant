<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useRouter } from 'vue-router'
import OAuthButtons from '@/components/auth/OAuthButtons.vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const error = ref<string | null>(null)
const route = useRoute()
const isLoading = ref(false)

const oauthErrorMessage = computed(() => {
  const code = route.query.oauth_error
  if (code === 'state_mismatch') {
    return 'Sign-in expired. Use Continue with GitHub again (OAuth runs on port 8000). Ensure GitHub callback is http://127.0.0.1:8000/api/auth/oauth/github/callback.'
  }
  if (code === 'failed') {
    return 'GitHub sign-in failed. Check API logs and that your GitHub account has a verified email.'
  }
  return null
})

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
    <p
      v-if="oauthErrorMessage"
      class="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
      role="alert"
    >
      {{ oauthErrorMessage }}
    </p>
    <OAuthButtons :disabled="isLoading" />

    <div class="relative py-2">
      <div class="absolute inset-0 flex items-center" aria-hidden="true">
        <div class="w-full border-t border-border" />
      </div>
      <div class="relative flex justify-center text-xs uppercase">
        <span class="bg-card px-2 text-muted-foreground">Or use password</span>
      </div>
    </div>

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
