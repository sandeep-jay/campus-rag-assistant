<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ChatSession } from '@/api/types'
import SessionItem from './SessionItem.vue'

const props = defineProps<{ sessions: ChatSession[]; activeSessionId: number | null }>()
const emit = defineEmits<{ select: [id: number]; delete: [id: number] }>()

const pendingDeleteId = ref<number | null>(null)

function getDateGroup(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterday = new Date(today.getTime() - 86400000)
  const thisWeekStart = new Date(today.getTime() - 6 * 86400000)

  const d = new Date(date.getFullYear(), date.getMonth(), date.getDate())

  if (d.getTime() === today.getTime()) return 'Today'
  if (d.getTime() === yesterday.getTime()) return 'Yesterday'
  if (d >= thisWeekStart) return 'This Week'
  return 'Older'
}

const groupOrder = ['Today', 'Yesterday', 'This Week', 'Older']

const groupedSessions = computed(() => {
  const groups: Record<string, ChatSession[]> = {}
  for (const session of props.sessions) {
    const group = getDateGroup(session.created_at)
    if (!groups[group]) groups[group] = []
    groups[group].push(session)
  }
  return groupOrder.filter((g) => groups[g]).map((g) => ({ label: g, sessions: groups[g] }))
})

const pendingDeleteSession = computed(() =>
  props.sessions.find((s) => s.id === pendingDeleteId.value) ?? null,
)

function requestDelete(id: number): void {
  pendingDeleteId.value = id
}

function cancelDelete(): void {
  pendingDeleteId.value = null
}

function confirmDelete(): void {
  if (pendingDeleteId.value == null) return
  emit('delete', pendingDeleteId.value)
  pendingDeleteId.value = null
}
</script>

<template>
  <nav aria-label="Sessions" class="relative flex-1 overflow-y-auto px-2 py-2">
    <div v-if="sessions.length === 0" class="px-3 py-8 text-center">
      <p class="text-sm text-muted-foreground">No conversations yet.</p>
      <p class="text-xs text-muted-foreground mt-1">Start a new chat to get help.</p>
    </div>

    <div v-for="group in groupedSessions" :key="group.label" class="mb-4">
      <h3 class="px-3 py-1 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
        {{ group.label }}
      </h3>
      <ul class="space-y-0.5">
        <SessionItem
          v-for="session in group.sessions"
          :key="session.id"
          :session="session"
          :is-active="activeSessionId === session.id"
          @select="emit('select', $event)"
          @request-delete="requestDelete"
        />
      </ul>
    </div>

    <div
      v-if="pendingDeleteSession"
      class="sticky bottom-2 z-20 mx-2 rounded-lg border border-border bg-background shadow-lg p-3"
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-confirm-title"
    >
      <p id="delete-confirm-title" class="text-sm font-medium text-foreground mb-1">
        Delete conversation?
      </p>
      <p class="text-xs text-muted-foreground mb-3 truncate">
        {{ pendingDeleteSession.title }}
      </p>
      <div class="flex gap-2">
        <button
          class="flex-1 rounded-md bg-destructive px-3 py-1.5 text-xs font-medium text-destructive-foreground hover:bg-destructive/90 transition-colors"
          @click="confirmDelete"
        >
          Delete
        </button>
        <button
          class="flex-1 rounded-md border border-border px-3 py-1.5 text-xs font-medium hover:bg-accent transition-colors"
          @click="cancelDelete"
        >
          Cancel
        </button>
      </div>
    </div>
  </nav>
</template>
