<script setup lang="ts">
import { computed, ref } from 'vue'
import { Check, Circle, ChevronDown, ChevronRight, X as XIcon } from 'lucide-vue-next'
import type { AgentStep } from '@/types/helpdesk'

// One compact, Cursor-style row per agent step. Source data comes from
// either ``AgentTurn.debug_trace`` (live in-memory bubble) or
// ``agent_summary.trace`` (persisted chat_messages row, reload-safe).
//
// We intentionally hide the raw {step, action, outcome} tuple behind
// humanized labels so the row reads as natural language. The original
// fields stay in the DOM via ``title`` attrs so admins / developers
// who want the technical detail still get it on hover.

const props = withDefaults(
  defineProps<{
    steps: AgentStep[]
    /** When true, render fully expanded; when false, render a single ``Steps (n) >`` toggle. */
    defaultExpanded?: boolean
    /** Marks this run as still running so the last row pulses. */
    isRunning?: boolean
  }>(),
  { defaultExpanded: false, isRunning: false },
)

const expanded = ref(props.defaultExpanded)

interface TimelineRow {
  key: string
  label: string
  detail: string | null
  status: 'done' | 'running' | 'waiting' | 'failed'
  raw: AgentStep
}

// Map raw debug-trace actions to human-friendly labels.
// Anything missing falls back to a sentence-cased action name.
const ACTION_LABELS: Record<string, string> = {
  search_existing_issues: 'Checked existing tickets',
  classify_ticket: 'Classified the issue',
  retry_kb: 'Knowledge base (agent retry)',
  web_search: 'Public web search',
  web_search_consent: 'Asked to use public web search',
  kb_low_confidence: 'KB hits below confidence floor',
  propose_solution: 'Proposed a solution',
  skip_propose_solution: 'Skipped proposing a solution',
  file_ticket: 'Filed the ticket',
  link_existing: 'Linked to an existing ticket',
  abort: 'Canceled the session',
  ask_user: 'Asked the user',
  append_user_reply: 'Recorded the user reply',
  write_draft: 'Drafted the ticket',
  solution_feedback: "Recorded the user\u2019s feedback",
  resolved_by_agent: 'Marked resolved without a ticket',
}

function humanize(action: string): string {
  if (ACTION_LABELS[action]) return ACTION_LABELS[action]
  return action
    .replace(/_/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/^./, (c) => c.toUpperCase())
}

function classifyStatus(outcome: string): TimelineRow['status'] {
  const o = (outcome || '').toLowerCase()
  if (o === 'waiting' || o === 'pending') return 'waiting'
  if (o === 'failed' || o === 'error' || o === 'denied') return 'failed'
  if (o === 'running') return 'running'
  return 'done'
}

const rows = computed<TimelineRow[]>(() => {
  return (props.steps || []).map((step, idx) => {
    const status = classifyStatus(step.outcome)
    const label = humanize(step.action)
    let detail: string | null = null
    const latency = typeof step.latency_ms === 'number' ? `${Math.round(step.latency_ms)}ms` : null
    if (step.message && step.message.trim()) {
      detail = latency ? `${step.message.trim()} · ${latency}` : step.message.trim()
    } else if (step.outcome && step.outcome.toLowerCase() !== 'success') {
      detail = latency ? `${step.outcome} · ${latency}` : step.outcome
    } else if (latency) {
      detail = latency
    }
    return {
      key: `${idx}-${step.action}-${step.outcome}`,
      label,
      detail,
      status,
      raw: step,
    }
  })
})

const hasRows = computed(() => rows.value.length > 0)
const toggleLabel = computed(() => `What the agent did (${rows.value.length})`)

function rowTitle(row: TimelineRow): string {
  return `${row.raw.step} \u2192 ${row.raw.action} (${row.raw.outcome})`
}
</script>

<template>
  <div v-if="hasRows" class="w-full text-chat-caption" data-testid="agent-activity-timeline">
    <button
      type="button"
      class="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
      :aria-expanded="expanded"
      aria-controls="agent-activity-list"
      @click="expanded = !expanded"
    >
      <ChevronDown v-if="expanded" class="h-3.5 w-3.5" aria-hidden="true" />
      <ChevronRight v-else class="h-3.5 w-3.5" aria-hidden="true" />
      <span class="font-medium">{{ toggleLabel }}</span>
    </button>

    <ol
      v-show="expanded"
      id="agent-activity-list"
      class="mt-2 space-y-1.5"
      :class="{ 'pl-1': !defaultExpanded }"
    >
      <li
        v-for="(row, idx) in rows"
        :key="row.key"
        class="flex items-start gap-2.5"
        :title="rowTitle(row)"
      >
        <span class="mt-[3px] flex h-3.5 w-3.5 shrink-0 items-center justify-center">
          <template v-if="row.status === 'done'">
            <span
              class="flex h-3.5 w-3.5 items-center justify-center rounded-full bg-accent-subtle text-accent-subtle-foreground"
              aria-hidden="true"
            >
              <Check class="h-2.5 w-2.5" />
            </span>
          </template>
          <template v-else-if="row.status === 'running' || (isRunning && idx === rows.length - 1)">
            <span
              class="h-2.5 w-2.5 rounded-full bg-primary animate-pulse motion-reduce:animate-none"
              aria-hidden="true"
            />
          </template>
          <template v-else-if="row.status === 'failed'">
            <span
              class="flex h-3.5 w-3.5 items-center justify-center rounded-full bg-destructive/15 text-destructive"
              aria-hidden="true"
            >
              <XIcon class="h-2.5 w-2.5" />
            </span>
          </template>
          <template v-else>
            <Circle class="h-2.5 w-2.5 text-muted-foreground" aria-hidden="true" />
          </template>
        </span>

        <div class="flex min-w-0 flex-1 items-baseline gap-2">
          <span class="text-foreground">{{ row.label }}</span>
          <span
            v-if="row.detail"
            class="truncate text-muted-foreground"
          >{{ row.detail }}</span>
        </div>
      </li>
    </ol>
  </div>
</template>
