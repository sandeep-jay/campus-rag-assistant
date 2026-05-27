<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ChevronDown, ChevronRight } from 'lucide-vue-next'
import type { ChatSession } from '@/api/types'
import SessionItem from './SessionItem.vue'

const props = defineProps<{ sessions: ChatSession[]; activeSessionId: number | null }>()
const emit = defineEmits<{ select: [id: number]; delete: [id: number] }>()

const pendingDeleteId = ref<number | null>(null)

// How many sessions to reveal per date group before requiring "Show more".
// Keeps the sidebar usable when there are dozens or hundreds of conversations.
const PAGE_SIZE = 8
const visibleCount = ref<Record<string, number>>({})

// Collapsed/expanded state per group, persisted to localStorage so a user's
// preferred view survives reloads. Today + active group default to expanded.
const STORAGE_KEY = 'campusrag.sidebar.collapsedGroups'

function loadCollapsed(): Record<string, boolean> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    return typeof parsed === 'object' && parsed !== null ? parsed : {}
  } catch {
    return {}
  }
}

const collapsed = ref<Record<string, boolean>>(loadCollapsed())

watch(
  collapsed,
  (next) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    } catch {
      // Storage may be disabled (private mode, quota); fall back to in-memory only.
    }
  },
  { deep: true },
)

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
  return groupOrder
    .filter((g) => groups[g])
    .map((g) => ({ label: g, sessions: groups[g] }))
})

// Default state: 'Today' is always expanded; older groups start collapsed
// unless the user has explicitly toggled them.
function isCollapsed(label: string): boolean {
  if (label in collapsed.value) return collapsed.value[label]
  return label !== 'Today'
}

function toggleGroup(label: string): void {
  collapsed.value = { ...collapsed.value, [label]: !isCollapsed(label) }
}

function shownInGroup(label: string, total: number): ChatSession[] {
  const limit = visibleCount.value[label] ?? PAGE_SIZE
  return groupedSessions.value.find((g) => g.label === label)?.sessions.slice(0, Math.min(limit, total)) ?? []
}

function showMore(label: string, total: number): void {
  const current = visibleCount.value[label] ?? PAGE_SIZE
  visibleCount.value = { ...visibleCount.value, [label]: Math.min(current + PAGE_SIZE, total) }
}

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

    <div v-for="group in groupedSessions" :key="group.label" class="mb-2">
      <button
        type="button"
        class="w-full flex items-center justify-between px-3 py-1 rounded-md hover:bg-sidebar-accent transition-colors text-left"
        :aria-expanded="!isCollapsed(group.label)"
        :aria-controls="`group-${group.label.replace(/\s+/g, '-').toLowerCase()}`"
        @click="toggleGroup(group.label)"
      >
        <span class="inline-flex items-center gap-1.5">
          <component
            :is="isCollapsed(group.label) ? ChevronRight : ChevronDown"
            class="h-3.5 w-3.5 text-muted-foreground"
            aria-hidden="true"
          />
          <span class="text-xs font-semibold text-sidebar-foreground uppercase tracking-wider">
            {{ group.label }}
          </span>
        </span>
        <span class="text-[10px] font-medium text-muted-foreground tabular-nums">
          {{ group.sessions.length }}
        </span>
      </button>

      <ul
        v-show="!isCollapsed(group.label)"
        :id="`group-${group.label.replace(/\s+/g, '-').toLowerCase()}`"
        class="space-y-0.5 mt-1"
      >
        <SessionItem
          v-for="session in shownInGroup(group.label, group.sessions.length)"
          :key="session.id"
          :session="session"
          :is-active="activeSessionId === session.id"
          @select="emit('select', $event)"
          @request-delete="requestDelete"
        />
        <li
          v-if="group.sessions.length > (visibleCount[group.label] ?? PAGE_SIZE)"
          class="pt-1"
        >
          <button
            type="button"
            class="w-full rounded-md px-3 py-1.5 text-xs text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground transition-colors text-left"
            @click="showMore(group.label, group.sessions.length)"
          >
            Show {{ Math.min(PAGE_SIZE, group.sessions.length - (visibleCount[group.label] ?? PAGE_SIZE)) }} more
            <span class="text-muted-foreground/70">
              ({{ group.sessions.length - (visibleCount[group.label] ?? PAGE_SIZE) }} hidden)
            </span>
          </button>
        </li>
      </ul>
    </div>

    <div
      v-if="pendingDeleteSession"
      class="sticky bottom-2 z-20 mx-2 rounded-lg border border-border bg-card shadow-pop p-3"
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
