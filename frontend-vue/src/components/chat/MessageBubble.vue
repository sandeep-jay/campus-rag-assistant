<script setup lang="ts">
import { ref, computed } from 'vue'
import { Copy, Check, Info } from 'lucide-vue-next'
import type { DisplayMessage, ChatMessage } from '@/api/types'
import { renderMarkdown } from '@/utils/markdown'
import MessageFeedback from './MessageFeedback.vue'
import SourcesPanel from './SourcesPanel.vue'
import SourcesSummary from './SourcesSummary.vue'
import HelpdeskActions from './HelpdeskActions.vue'
import AgentTurnActions from './AgentTurnActions.vue'
import AgentTurnBadge from './AgentTurnBadge.vue'
import AgentActivityTimeline from './AgentActivityTimeline.vue'

const props = defineProps<{ message: DisplayMessage; isStreaming?: boolean; isLastMessage?: boolean }>()

const isCopied = ref(false)
const showSources = ref(false)

function isAssistant(msg: DisplayMessage): boolean {
  return msg.role === 'assistant'
}

function isOptimistic(msg: DisplayMessage): boolean {
  return 'isOptimistic' in msg
}

function getSources(msg: DisplayMessage): ChatMessage['metadata'] {
  if ('metadata' in msg) return msg.metadata
  return undefined
}

const sources = computed(() => {
  const meta = getSources(props.message)
  if (meta?.sources?.length) return meta.sources
  if (meta?.agent_turn?.sources?.length) return meta.agent_turn.sources
  if (meta?.agent_summary?.sources?.length) return meta.agent_summary.sources
  return []
})
const documentContents = computed(() => {
  const meta = getSources(props.message)
  if (meta?.document_contents?.length) return meta.document_contents
  if (meta?.agent_turn?.document_contents?.length) return meta.agent_turn.document_contents
  if (meta?.agent_summary?.document_contents?.length) return meta.agent_summary.document_contents
  return []
})
const hasSources = computed(
  () => sources.value.length > 0 || documentContents.value.length > 0,
)

const disclaimer = computed(() => {
  const meta = getSources(props.message)
  return meta?.disclaimer ?? meta?.agent_turn?.disclaimer ?? meta?.agent_summary?.disclaimer ?? null
})

const kbResolved = computed(() => getSources(props.message)?.kb_resolved ?? null)
const routerDecision = computed(() => getSources(props.message)?.router_decision ?? null)
const agentTurn = computed(() => getSources(props.message)?.agent_turn ?? null)
const agentSummary = computed(() => getSources(props.message)?.agent_summary ?? null)
// Phase 5 escalation chip gate: the helpdesk action chip fires when the
// KB path could not answer OR the campus router classified the turn as
// 'helpdesk' with confidence at or above the configured floor. The
// floor mirrors backend ``ROUTER_HELPDESK_FLOOR`` (default 0.6); the
// backend gates the same way for the SSE/non-SSE responses.
const ROUTER_HELPDESK_FLOOR = 0.6
const routerWantsHelpdesk = computed(() => {
  const decision = routerDecision.value
  if (!decision || decision.domain !== 'helpdesk') return false
  return decision.confidence >= ROUTER_HELPDESK_FLOOR
})
const terminalKinds: ReadonlyArray<string> = ['filed', 'linked', 'resolved', 'aborted']
// Derive the badge payload from EITHER the live AgentTurn or the
// persisted ``agent_summary`` metadata so the badge (and its issue
// link) survives a page reload. ``agent_turn`` wins when both exist
// because it carries the most recent in-memory state.
const terminalBadge = computed<{ kind: string; linked_issue_url: string | null } | null>(() => {
  if (agentTurn.value && terminalKinds.includes(String(agentTurn.value.kind))) {
    return {
      kind: String(agentTurn.value.kind),
      linked_issue_url: agentTurn.value.linked_issue_url ?? null,
    }
  }
  if (agentSummary.value) {
    return {
      kind: agentSummary.value.kind,
      linked_issue_url: agentSummary.value.linked_issue_url ?? null,
    }
  }
  return null
})

// Timeline source: prefer the live ``debug_trace`` when an ``agent_turn``
// is present (the agent is still running or just terminated in this
// session), else fall back to the persisted ``agent_summary.trace`` so
// reloaded conversations still render the full step list.
const agentTimelineSteps = computed(() => {
  if (agentTurn.value?.debug_trace?.length) return agentTurn.value.debug_trace
  if (agentSummary.value?.trace?.length) return agentSummary.value.trace
  return []
})

// We treat any non-terminal ``agent_turn`` (``question`` / ``info`` /
// ``draft_ready``) as 'still running' so the last timeline row pulses.
// Older bubbles in a multi-turn agent session are no longer active, so
// only the bottom-most bubble can be 'running' — gating by
// ``isLastMessage`` prevents the spinner/pulse on past turns once the
// agent has produced a new turn below.
const isAgentRunning = computed(() => {
  if (!agentTurn.value) return false
  if (!(props.isLastMessage ?? false)) return false
  return !terminalKinds.includes(String(agentTurn.value.kind))
})

// Only the bottom-most agent bubble carries an actionable turn; older
// bubbles in the same agent session keep their text and timeline but
// must not show clickable pills/radios that the user has already
// answered. See ``AgentTurnActions.appendAgentTurn`` — each agent reply
// is appended as a new bubble, so the previous bubble is no longer the
// last message and its choices freeze into read-only history.
const showAgentTurnActions = computed(
  () => Boolean(agentTurn.value) && (props.isLastMessage ?? false),
)

const showHelpdeskActions = computed(
  () =>
    isAssistant(props.message) &&
    !agentTurn.value &&
    (props.isLastMessage ?? false) &&
    (kbResolved.value === false || routerWantsHelpdesk.value),
)

const panelId = computed(() => {
  const id = 'id' in props.message ? String((props.message as { id: number | string }).id) : 'opt'
  return `sources-panel-${id}`
})

async function copyMessage(): Promise<void> {
  try {
    await navigator.clipboard.writeText(props.message.content)
    isCopied.value = true
    setTimeout(() => { isCopied.value = false }, 2000)
  } catch {
    // clipboard not available
  }
}

function formatTime(dateStr: string): string {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <article
    class="w-full py-3 px-4 sm:px-6 lg:px-8"
    :class="isAssistant(message) ? '' : ''"
    :data-testid="isAssistant(message) ? 'assistant-bubble' : 'user-bubble'"
  >
    <!-- Assistant: avatar left, content right -->
    <div v-if="isAssistant(message)" class="chat-container flex gap-3 items-start">
      <div
        class="flex-shrink-0 h-9 w-9 rounded-full flex items-center justify-center text-chat-avatar font-bold uppercase bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-100"
        aria-hidden="true"
      >
        AI
      </div>

      <div class="group/bubble flex min-w-0 flex-1 flex-col gap-1.5 items-start max-w-[95%]">
        <span class="text-chat-label text-muted-foreground px-1">Assistant</span>

        <div
          v-if="isStreaming"
          class="w-full rounded-lg border border-border bg-card px-5 py-4 shadow-soft"
          aria-live="polite"
          aria-atomic="false"
        >
          <p
            v-if="message.content"
            class="whitespace-pre-wrap break-words text-chat-body text-foreground"
          >
            {{ message.content }}
          </p>
          <p v-else class="text-chat-caption text-muted-foreground">Preparing answer…</p>
          <span
            class="inline-block w-0.5 h-4 ml-0.5 bg-primary align-middle animate-pulse motion-reduce:animate-none"
            aria-hidden="true"
          />
        </div>

        <div v-else class="w-full rounded-lg border border-border bg-card px-5 py-4 shadow-soft">
          <div v-if="terminalBadge" class="mb-3">
            <AgentTurnBadge :kind="terminalBadge.kind" :linked_issue_url="terminalBadge.linked_issue_url" />
          </div>

          <AgentActivityTimeline
            v-if="agentTimelineSteps.length"
            :steps="agentTimelineSteps"
            :default-expanded="isAgentRunning"
            :is-running="isAgentRunning"
            class="mb-3 border-b border-border pb-3"
          />

          <div class="chat-prose dark:prose-invert max-w-none text-foreground" v-html="renderMarkdown(message.content)" />

          <!-- Escalation prompt + actions live inside the same card so a
               'no KB match' response reads as one assistant turn, not two
               stacked components. -->
          <HelpdeskActions v-if="showHelpdeskActions && !isStreaming" />
        </div>

        <p
          v-if="disclaimer && !isStreaming"
          class="flex w-full items-start gap-2 rounded-md border border-border bg-muted px-3 py-2 text-chat-caption text-muted-foreground"
          role="note"
          data-testid="web-disclaimer"
        >
          <Info class="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent-subtle-foreground" aria-hidden="true" />
          <span>{{ disclaimer }}</span>
        </p>

        <AgentTurnActions v-if="showAgentTurnActions && !isStreaming" :turn="agentTurn!" />

        <span class="text-chat-meta text-muted-foreground px-1">
          {{ formatTime(message.created_at) }}
        </span>

        <div
          v-if="!isOptimistic(message) && !isStreaming"
          class="flex w-full flex-col gap-2"
        >
          <!-- Always visible message actions: feedback + copy live in the
               same row so users get the same affordances they expect from
               other chat tools (ChatGPT / Claude). No hover-to-reveal so
               the copy action is discoverable on touch + screen readers. -->
          <div class="flex w-full items-center gap-1">
            <MessageFeedback :message-id="message.id as number" />
            <button
              type="button"
              :aria-label="isCopied ? 'Copied to clipboard' : 'Copy message to clipboard'"
              class="inline-flex items-center gap-1 rounded-md p-1.5 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
              @click="copyMessage"
            >
              <Check v-if="isCopied" class="h-4 w-4 text-green-600" aria-hidden="true" />
              <Copy v-else class="h-4 w-4" aria-hidden="true" />
              <span v-if="isCopied" class="text-xs text-green-700 dark:text-green-400">Copied</span>
            </button>
          </div>

          <template v-if="hasSources">
            <SourcesSummary
              :sources="sources"
              :expanded="showSources"
              :panel-id="panelId"
              :document-contents-count="documentContents.length"
              @toggle="showSources = !showSources"
            />
            <div v-if="showSources" :id="panelId" class="w-full">
              <SourcesPanel :sources="sources" :document-contents="documentContents" />
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- User: content + avatar grouped on the right -->
    <div v-else class="chat-container flex justify-end">
      <div class="flex max-w-[min(85%,40rem)] gap-3 items-end">
        <div class="group/bubble flex min-w-0 flex-col gap-1.5 items-end">
          <span class="text-chat-label user-message-label px-1">You</span>

          <div
            class="user-message-bubble rounded-lg px-4 py-3 shadow-soft"
            :class="isOptimistic(message) ? 'opacity-70' : ''"
          >
            <p class="whitespace-pre-wrap break-words text-chat-body">
              {{ message.content }}
            </p>
          </div>

          <span class="text-chat-meta text-muted-foreground px-1">
            {{ formatTime(message.created_at) }}
          </span>
        </div>

        <div
          class="flex-shrink-0 h-9 w-9 rounded-full flex items-center justify-center text-chat-avatar font-bold uppercase user-message-avatar"
          aria-hidden="true"
        >
          Y
        </div>
      </div>
    </div>
  </article>
</template>
