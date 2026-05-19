<script setup lang="ts">
defineProps<{
  disabled?: boolean
}>()

const providers = ['github'] as const

function oauthLogin(provider: string): void {
  window.location.href = `/api/auth/oauth/${provider}`
}

function label(provider: string): string {
  return provider === 'google' ? 'Continue with Google' : 'Continue with GitHub'
}
</script>

<template>
  <div class="space-y-3">
    <button
      v-for="provider in providers"
      :key="provider"
      type="button"
      :disabled="disabled"
      class="w-full rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
      @click="oauthLogin(provider)"
    >
      {{ label(provider) }}
    </button>
  </div>
</template>
