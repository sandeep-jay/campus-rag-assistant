import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  abortAgentSession,
  confirmAgentSession,
  createIssue,
  draftTicket,
  recapConversation,
  resumeAgentSession,
  startAgentSession,
  streamResumeAgentSession,
  streamStartAgentSession,
} from '@/api/helpdesk'
import type {
  AgentStep,
  AgentStreamStepEvent,
  AgentTurn,
  ConversationSummary,
  ConversationTurn,
  CreateIssueResponse,
  TicketDraft,
} from '@/types/helpdesk'
import { trackHelpdeskAgentEvent } from '@/utils/telemetry'

export const useHelpdeskStore = defineStore('helpdesk', () => {
  const modalOpen = ref(false)
  // Distinct loading flags per agent task so a Summarize in flight does
  // not visually block Create ticket (and vice versa), and so the
  // component can choose which spinner to show.
  const recapping = ref(false)
  const drafting = ref(false)
  const submitting = ref(false)
  const agentRunning = ref(false)
  const agentStatus = ref<string | null>(null)
  const agentSteps = ref<AgentStep[]>([])
  const draft = ref<TicketDraft | null>(null)
  const activeTurn = ref<AgentTurn | null>(null)
  const result = ref<CreateIssueResponse | null>(null)
  const error = ref<string | null>(null)
  // Element to return focus to when the modal closes (a11y).
  const triggerEl = ref<HTMLElement | null>(null)

  // POST /api/helpdesk/summarize — narrative recap for inline display.
  // Does not touch `draft`; the modal flow has its own draftTicket call.
  async function recap(
    conversation: ConversationTurn[],
  ): Promise<ConversationSummary | null> {
    recapping.value = true
    error.value = null
    try {
      return await recapConversation(conversation)
    } catch {
      error.value = 'Failed to summarize. Please try again.'
      return null
    } finally {
      recapping.value = false
    }
  }

  // POST /api/helpdesk/draft-ticket — structured draft for the review
  // modal. Replaces any previous draft so the modal always reflects the
  // freshest extraction.
  async function makeDraft(
    conversation: ConversationTurn[],
  ): Promise<TicketDraft | null> {
    drafting.value = true
    error.value = null
    try {
      const next = await draftTicket(conversation)
      draft.value = next
      return next
    } catch {
      error.value = 'Failed to draft a ticket. Please try again.'
      return null
    } finally {
      drafting.value = false
    }
  }

  async function startAgent(
    conversation: ConversationTurn[],
    chat_session_id?: number | null,
  ): Promise<AgentTurn | null> {
    agentRunning.value = true
    error.value = null
    agentSteps.value = []
    trackHelpdeskAgentEvent('start_requested', { turn_count: conversation.length })
    try {
      let turn: AgentTurn
      try {
        turn = await streamStartAgentSession(
          conversation,
          chat_session_id ?? null,
          updateAgentStatus,
          recordAgentStreamStep,
        )
      } catch {
        trackHelpdeskAgentEvent('stream_fallback', { operation: 'start' })
        turn = await startAgentSession(conversation, chat_session_id ?? null)
      }
      recordAgentTurn(turn)
      trackHelpdeskAgentEvent('start_completed', { kind: turn.kind, has_draft: Boolean(turn.draft) })
      return turn
    } catch {
      trackHelpdeskAgentEvent('start_failed')
      error.value = 'Failed to start helpdesk agent. Please try again.'
      return null
    } finally {
      agentRunning.value = false
      agentStatus.value = null
      agentSteps.value = []
    }
  }

  async function resumeAgent(params: {
    session_id: string
    reply?: string
    choice?: string
    pending_question_id?: string
    chat_session_id?: number | null
  }): Promise<AgentTurn | null> {
    agentRunning.value = true
    error.value = null
    agentSteps.value = []
    trackHelpdeskAgentEvent('resume_requested', { has_choice: Boolean(params.choice), has_reply: Boolean(params.reply) })
    try {
      let turn: AgentTurn
      try {
        turn = await streamResumeAgentSession(params, updateAgentStatus, recordAgentStreamStep)
      } catch {
        trackHelpdeskAgentEvent('stream_fallback', { operation: 'resume' })
        turn = await resumeAgentSession(params)
      }
      recordAgentTurn(turn)
      trackHelpdeskAgentEvent('resume_completed', { kind: turn.kind, has_draft: Boolean(turn.draft) })
      return turn
    } catch {
      trackHelpdeskAgentEvent('resume_failed')
      error.value = 'Failed to continue helpdesk agent. Please try again.'
      return null
    } finally {
      agentRunning.value = false
      agentStatus.value = null
      agentSteps.value = []
    }
  }

  async function abortAgent(
    sessionId: string,
    chat_session_id?: number | null,
  ): Promise<AgentTurn | null> {
    agentRunning.value = true
    error.value = null
    try {
      const turn = await abortAgentSession(sessionId, chat_session_id ?? null)
      recordAgentTurn(turn)
      trackHelpdeskAgentEvent('abort_completed')
      return turn
    } catch {
      trackHelpdeskAgentEvent('abort_failed')
      error.value = 'Failed to cancel helpdesk agent. Please try again.'
      return null
    } finally {
      agentRunning.value = false
    }
  }

  function recordAgentTurn(turn: AgentTurn): void {
    activeTurn.value = ['resolved', 'aborted', 'filed', 'linked'].includes(turn.kind) ? null : turn
    if (turn.draft) {
      draft.value = turn.draft
    }
  }

  function updateAgentStatus(message: string): void {
    agentStatus.value = message
  }

  function recordAgentStreamStep(event: AgentStreamStepEvent): void {
    const step: AgentStep = {
      step: event.node,
      action: event.action,
      outcome: event.status,
      message: event.summary,
      latency_ms: event.latency_ms,
    }
    const duplicateRunningIndex = agentSteps.value.findIndex(
      (existing) =>
        existing.step === step.step &&
        existing.action === step.action &&
        existing.outcome === 'running',
    )
    if (duplicateRunningIndex >= 0 && step.outcome !== 'running') {
      agentSteps.value = [
        ...agentSteps.value.slice(0, duplicateRunningIndex),
        step,
        ...agentSteps.value.slice(duplicateRunningIndex + 1),
      ]
      agentStatus.value = event.summary
      return
    }
    agentSteps.value = [...agentSteps.value, step]
    agentStatus.value = event.summary
  }

  function clearAgentTurn(): void {
    activeTurn.value = null
  }

  function openModal(trigger?: HTMLElement | null): void {
    triggerEl.value = trigger ?? null
    modalOpen.value = true
    trackHelpdeskAgentEvent('draft_review_opened', { source: activeTurn.value?.kind === 'draft_ready' ? 'agent' : 'manual' })
  }

  function closeModal(): void {
    modalOpen.value = false
    const trigger = triggerEl.value
    triggerEl.value = null
    if (trigger && typeof trigger.focus === 'function') {
      setTimeout(() => trigger.focus(), 0)
    }
  }

  async function confirmAgent(
    sessionId: string,
    reviewed: TicketDraft,
    chat_session_id?: number | null,
  ): Promise<AgentTurn | null> {
    submitting.value = true
    error.value = null
    try {
      const turn = await confirmAgentSession(sessionId, reviewed, chat_session_id ?? null)
      recordAgentTurn(turn)
      modalOpen.value = false
      trackHelpdeskAgentEvent('confirm_completed', { kind: turn.kind })
      return turn
    } catch {
      trackHelpdeskAgentEvent('confirm_failed')
      error.value = 'Failed to file agent ticket. Please try again.'
      return null
    } finally {
      submitting.value = false
    }
  }

  async function submitIssue(
    reviewed: TicketDraft,
  ): Promise<CreateIssueResponse | null> {
    submitting.value = true
    error.value = null
    try {
      const next = await createIssue(reviewed)
      result.value = next
      modalOpen.value = false
      return next
    } catch {
      error.value = 'Failed to create issue. Please try again.'
      return null
    } finally {
      submitting.value = false
    }
  }

  function reset(): void {
    modalOpen.value = false
    recapping.value = false
    drafting.value = false
    submitting.value = false
    agentRunning.value = false
    agentStatus.value = null
    agentSteps.value = []
    activeTurn.value = null
    draft.value = null
    result.value = null
    error.value = null
    triggerEl.value = null
  }

  return {
    modalOpen,
    recapping,
    drafting,
    submitting,
    agentRunning,
    agentStatus,
    agentSteps,
    activeTurn,
    draft,
    result,
    error,
    triggerEl,
    recap,
    makeDraft,
    startAgent,
    resumeAgent,
    abortAgent,
    confirmAgent,
    recordAgentTurn,
    clearAgentTurn,
    openModal,
    closeModal,
    submitIssue,
    reset,
  }
})
