<script setup lang="ts">
import { Sun, Moon, PanelLeft } from 'lucide-vue-next'
import { useDarkMode } from '@/composables/useDarkMode'

defineEmits<{ 'toggle-sidebar': [] }>()

const { isDark, toggle } = useDarkMode()
</script>

<template>
  <header class="flex items-center justify-between border-b border-border bg-card px-4 h-14 flex-shrink-0">
    <div class="flex items-center gap-3">
      <button
        aria-label="Toggle sidebar"
        class="rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors md:hidden"
        @click="$emit('toggle-sidebar')"
      >
        <PanelLeft class="h-5 w-5" aria-hidden="true" />
      </button>
      <div class="flex items-center gap-2">
        <span class="text-chat-ui font-semibold text-foreground">Campus RAG Assistant</span>
        <span class="hidden sm:inline text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full">Beta</span>
      </div>
    </div>

    <div class="flex items-center gap-2">
      <button
        :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
        class="rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
        @click="toggle"
      >
        <Sun v-if="isDark" class="h-5 w-5" aria-hidden="true" />
        <Moon v-else class="h-5 w-5" aria-hidden="true" />
      </button>
      <slot name="user-menu" />
    </div>
  </header>
</template>
