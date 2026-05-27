<script setup lang="ts">
import { computed } from 'vue'
import { CheckCircle2, GitPullRequestArrow, Link2, XCircle } from 'lucide-vue-next'

// Minimal shape covering both the live ``AgentTurn`` (in-memory bubble)
// and the persisted ``agent_summary`` metadata (reloaded chat_message),
// so the badge renders identically before and after a refresh.
type TerminalKind = 'filed' | 'linked' | 'resolved' | 'aborted'
const props = defineProps<{
  kind: TerminalKind | string
  linked_issue_url?: string | null
}>()

interface BadgeShape {
  icon: typeof CheckCircle2
  label: string
  tone: string
}

const badge = computed<BadgeShape | null>(() => {
  switch (props.kind) {
    case 'filed':
      return {
        icon: GitPullRequestArrow,
        label: 'Ticket filed',
        // Action outcomes use the app's single accent family so the badge
        // belongs to the rest of the chat chrome instead of looking like a
        // status pill from a dashboard.
        tone: 'bg-accent-subtle text-accent-subtle-foreground border-accent-subtle',
      }
    case 'linked':
      return {
        icon: Link2,
        label: 'Linked to existing issue',
        tone: 'bg-accent-subtle text-accent-subtle-foreground border-accent-subtle',
      }
    case 'resolved':
      return {
        icon: CheckCircle2,
        label: 'Marked resolved',
        // Resolved is the one truly affirmative terminal state -- one calm
        // green (not emerald-50 sticker green) so it reads as positive
        // confirmation rather than a marketing badge.
        tone: 'bg-success-subtle text-success-subtle-foreground border-success-subtle',
      }
    case 'aborted':
      return {
        icon: XCircle,
        label: 'Helpdesk session cancelled',
        tone: 'bg-muted text-muted-foreground border-border',
      }
    default:
      return null
  }
})

const issueRef = computed<string | null>(() => {
  if (!props.linked_issue_url) return null
  const match = props.linked_issue_url.match(/\/issues\/(\d+)/)
  return match ? `#${match[1]}` : null
})
</script>

<template>
  <div
    v-if="badge"
    class="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-chat-caption font-medium"
    :class="badge.tone"
    data-testid="agent-turn-badge"
  >
    <component :is="badge.icon" class="h-3.5 w-3.5" aria-hidden="true" />
    <span>{{ badge.label }}</span>
    <a
      v-if="linked_issue_url"
      :href="linked_issue_url"
      target="_blank"
      rel="noopener noreferrer"
      class="underline underline-offset-2 decoration-current/60 hover:decoration-current"
    >
      {{ issueRef ?? 'View' }}
    </a>
  </div>
</template>
