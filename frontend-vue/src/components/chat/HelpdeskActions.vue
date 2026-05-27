<script setup lang="ts">
import { computed, ref } from 'vue'
import { Bot, LifeBuoy, FileText } from 'lucide-vue-next'
import { useChatStore } from '@/stores/chat'
import { useHelpdeskStore } from '@/stores/helpdesk'
import type {
  AgentTurn,
  ConversationSummary,
  ConversationTurn,
  TicketDraft,
} from '@/types/helpdesk'

const chat = useChatStore()
const helpdesk = useHelpdeskStore()

const summarizeBtn = ref<HTMLButtonElement | null>(null)
const ticketBtn = ref<HTMLButtonElement | null>(null)
const activeAction = ref<'summarize' | 'ticket' | 'agent' | null>(null)
// Prevents the user from appending the same recap twice in a row from
// this actions block. Create ticket is unaffected — it runs an
// independent draft_ticket call against the latest conversation.
const summarized = ref(false)

const recapping = computed(() => helpdesk.recapping)
const drafting = computed(() => helpdesk.drafting)
const submitting = computed(() => helpdesk.submitting)
const agentRunning = computed(() => helpdesk.agentRunning)

const summarizeDisabled = computed(
  () => summarized.value || recapping.value || submitting.value || agentRunning.value,
)
const ticketDisabled = computed(
  () => drafting.value || submitting.value || agentRunning.value,
)
const agentDisabled = computed(() => agentRunning.value || submitting.value)

function conversationPayload(): ConversationTurn[] {
  return chat.currentMessages.map((m) => ({
    role: m.role,
    content: m.content,
  }))
}

function formatRecapMarkdown(summary: ConversationSummary): string {
  // The recap endpoint already returns Markdown; we wrap it in a
  // labelled section so the user can see it's an AI-generated overview
  // of the conversation and not the assistant's normal answer.
  return ['**Conversation recap (AI-generated)**', '', summary.summary.trim()].join('\n')
}

async function handleSummarize(): Promise<void> {
  if (summarizeDisabled.value) return
  activeAction.value = 'summarize'
  // Summarize hits /api/helpdesk/summarize and returns a narrative
  // recap. It is independent of the Create ticket flow: it does not
  // populate helpdesk.draft, and Create ticket will re-extract a
  // ticket-shaped draft from the latest conversation when clicked.
  const recap = await helpdesk.recap(conversationPayload())
  if (recap) {
    chat.addAssistantMessage(formatRecapMarkdown(recap), { kb_resolved: false })
    summarized.value = true
  }
  activeAction.value = null
}

async function handleCreateTicket(): Promise<void> {
  if (ticketDisabled.value) return
  activeAction.value = 'ticket'
  // Always re-extract a ticket draft against the current conversation
  // so the modal reflects the freshest context. No coupling to the
  // inline recap above.
  const ticket: TicketDraft | null = await helpdesk.makeDraft(conversationPayload())
  if (ticket) {
    helpdesk.openModal(ticketBtn.value)
  }
  activeAction.value = null
}

function appendAgentTurn(turn: AgentTurn): void {
  helpdesk.recordAgentTurn(turn)
  chat.setChatMode('agent')
  chat.recordAgentTurnIntoChat(turn.message, turn)
  if (turn.draft) {
    helpdesk.openModal(ticketBtn.value)
  }
}

async function handleGetHelp(): Promise<void> {
  if (agentDisabled.value) return
  activeAction.value = 'agent'
  const turn = await helpdesk.startAgent(conversationPayload(), chat.activeSessionId)
  if (turn) appendAgentTurn(turn)
  activeAction.value = null
}
</script>

<template>
  <div
    class="w-full mt-4 border-t border-border pt-3"
    data-testid="helpdesk-actions"
    role="group"
    aria-label="Escalate this question"
  >
    <p class="text-chat-caption text-muted-foreground mb-2">
      I don’t have a knowledge-base match for this. What would you like to do next?
    </p>
    <div class="flex flex-wrap gap-2">
      <button
        ref="summarizeBtn"
        type="button"
        class="inline-flex items-center gap-2 rounded-md border border-border bg-card px-3 py-1.5 text-chat-ui hover:bg-accent hover:text-accent-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 disabled:cursor-not-allowed"
        :disabled="summarizeDisabled"
        @click="handleSummarize"
      >
        <FileText class="h-4 w-4" aria-hidden="true" />
        <span v-if="recapping && activeAction === 'summarize'">Summarizing&hellip;</span>
        <span v-else-if="summarized">Summary added</span>
        <span v-else>Summarize issue</span>
      </button>


      <button
        type="button"
        class="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-1.5 text-primary-foreground text-chat-ui hover:bg-primary/90 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 disabled:cursor-not-allowed"
        :disabled="agentDisabled"
        @click="handleGetHelp"
      >
        <Bot class="h-4 w-4" aria-hidden="true" />
        <span v-if="agentRunning && activeAction === 'agent'">Getting help&hellip;</span>
        <span v-else>Get help</span>
      </button>

      <button
        ref="ticketBtn"
        type="button"
        class="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-1.5 text-primary-foreground text-chat-ui hover:bg-primary/90 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 disabled:cursor-not-allowed"
        :disabled="ticketDisabled"
        @click="handleCreateTicket"
      >
        <LifeBuoy class="h-4 w-4" aria-hidden="true" />
        <span v-if="drafting && activeAction === 'ticket'">Drafting&hellip;</span>
        <span v-else>Create ticket</span>
      </button>
    </div>
    <p
      v-if="helpdesk.error"
      class="mt-2 text-chat-caption text-red-700 dark:text-red-300"
      role="alert"
    >
      {{ helpdesk.error }}
    </p>
  </div>
</template>
