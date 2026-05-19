<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import client from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const error = ref<string | null>(null)

onMounted(async () => {
  const code = route.query.code
  if (typeof code !== 'string' || !code) {
    error.value = 'Missing sign-in code. Try GitHub login again.'
    return
  }
  try {
    await client.post('/api/auth/oauth/handoff', { code })
    await auth.fetchCurrentUser()
    await router.replace('/chat')
  } catch {
    error.value = 'Could not complete sign-in. Try GitHub login again.'
  }
})
</script>

<template>
  <div v-if="error" class="flex min-h-screen items-center justify-center p-6">
    <p class="text-destructive" role="alert">{{ error }}</p>
  </div>
  <div v-else class="flex min-h-screen items-center justify-center p-6 text-muted-foreground">
    Completing sign-in…
  </div>
</template>
