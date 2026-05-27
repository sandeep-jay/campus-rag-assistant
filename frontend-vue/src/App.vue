<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Toaster } from 'vue-sonner'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import SkipLink from '@/components/layout/SkipLink.vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import UserMenu from '@/components/layout/UserMenu.vue'
import AppSidebar from '@/components/sidebar/AppSidebar.vue'
import TicketModal from '@/components/chat/TicketModal.vue'

const authStore = useAuthStore()
const { isAuthenticated } = storeToRefs(authStore)
const route = useRoute()

const sidebarOpen = ref(false)

watch(
  () => route.fullPath,
  () => {
    sidebarOpen.value = false
  },
)
</script>

<template>
  <div class="min-h-screen bg-background text-foreground">
    <SkipLink />
    <Toaster position="top-right" richColors />

    <div v-if="isAuthenticated" class="flex h-screen overflow-hidden">
      <div
        v-if="sidebarOpen"
        class="fixed inset-0 z-40 bg-black/50 md:hidden"
        aria-hidden="true"
        @click="sidebarOpen = false"
      />

      <AppSidebar :open="sidebarOpen" @close="sidebarOpen = false" />

      <div class="flex flex-col flex-1 min-w-0 overflow-hidden">
        <AppHeader @toggle-sidebar="sidebarOpen = !sidebarOpen">
          <template #user-menu>
            <UserMenu />
          </template>
        </AppHeader>

        <RouterView />
      </div>
    </div>

    <RouterView v-else />

    <TicketModal />
  </div>
</template>
