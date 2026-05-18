<script setup lang="ts">
import { ref } from 'vue'
import { Toaster } from 'vue-sonner'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import SkipLink from '@/components/layout/SkipLink.vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import UserMenu from '@/components/layout/UserMenu.vue'
import AppSidebar from '@/components/sidebar/AppSidebar.vue'

const authStore = useAuthStore()
const { isAuthenticated } = storeToRefs(authStore)

const sidebarOpen = ref(false)

</script>

<template>
  <div class="min-h-screen bg-background text-foreground">
    <SkipLink />
    <Toaster position="top-right" richColors />

    <!-- Authenticated layout -->
    <div v-if="isAuthenticated" class="flex h-screen overflow-hidden">
      <AppSidebar :open="sidebarOpen" @close="sidebarOpen = false" />

      <div class="flex flex-col flex-1 overflow-hidden">
        <AppHeader @toggle-sidebar="sidebarOpen = !sidebarOpen">
          <template #user-menu>
            <UserMenu />
          </template>
        </AppHeader>

        <RouterView />
      </div>
    </div>

    <!-- Unauthenticated layout -->
    <RouterView v-else />
  </div>
</template>
