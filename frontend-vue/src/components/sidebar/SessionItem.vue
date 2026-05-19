<script setup lang="ts">
import { Trash2, MessageSquare } from 'lucide-vue-next'
import type { ChatSession } from '@/api/types'

defineProps<{ session: ChatSession; isActive: boolean }>()
const emit = defineEmits<{ select: [id: number]; requestDelete: [id: number] }>()
</script>

<template>
  <li class="group relative">
    <button
      :aria-label="session.title"
      :aria-current="isActive ? 'page' : undefined"
      :title="session.title"
      class="w-full flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-left hover:bg-accent hover:text-accent-foreground transition-colors"
      :class="isActive ? 'bg-accent text-accent-foreground font-medium' : 'text-foreground'"
      @click="emit('select', session.id)"
    >
      <MessageSquare class="h-4 w-4 flex-shrink-0 text-muted-foreground" aria-hidden="true" />
      <span class="flex-1 truncate" :title="session.title">{{ session.title }}</span>
    </button>

    <button
      type="button"
      :aria-label="`Delete: ${session.title}`"
      class="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all focus:opacity-100"
      @click.stop="emit('requestDelete', session.id)"
    >
      <Trash2 class="h-3.5 w-3.5" aria-hidden="true" />
    </button>
  </li>
</template>
