<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { LogOut } from 'lucide-vue-next'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const { user } = storeToRefs(authStore)
const { logout } = authStore

const menuOpen = ref(false)

async function handleLogout(): Promise<void> {
  menuOpen.value = false
  await logout()
  await router.push('/login')
}
</script>

<template>
  <div class="relative">
    <button
      :aria-label="`User menu for ${user?.username ?? 'user'}`"
      :aria-expanded="menuOpen"
      class="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
      @click="menuOpen = !menuOpen"
    >
      <div class="h-7 w-7 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-xs font-bold" aria-hidden="true">
        {{ user?.username?.charAt(0).toUpperCase() ?? 'U' }}
      </div>
      <span class="hidden sm:inline max-w-24 truncate">{{ user?.username }}</span>
    </button>

    <!-- Dropdown menu -->
    <div
      v-if="menuOpen"
      class="absolute right-0 top-full mt-1 w-48 rounded-md border border-border bg-background shadow-lg z-20"
      role="menu"
    >
      <div class="px-3 py-2 border-b border-border">
        <p class="text-xs font-medium text-foreground truncate">{{ user?.username }}</p>
        <p class="text-xs text-muted-foreground truncate">{{ user?.email }}</p>
      </div>
      <button
        role="menuitem"
        aria-label="Log out"
        class="w-full flex items-center gap-2 px-3 py-2 text-sm text-foreground hover:bg-accent transition-colors"
        @click="handleLogout"
      >
        <LogOut class="h-4 w-4" aria-hidden="true" />
        Log out
      </button>
    </div>

    <!-- Backdrop to close menu -->
    <div
      v-if="menuOpen"
      class="fixed inset-0 z-10"
      aria-hidden="true"
      @click="menuOpen = false"
    />
  </div>
</template>
