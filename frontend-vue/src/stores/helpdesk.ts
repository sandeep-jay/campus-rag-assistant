import { defineStore } from 'pinia'
import { ref } from 'vue'
import { createIssue, draftTicket, recapConversation } from '@/api/helpdesk'
import type {
  ConversationSummary,
  ConversationTurn,
  CreateIssueResponse,
  TicketDraft,
} from '@/types/helpdesk'

export const useHelpdeskStore = defineStore('helpdesk', () => {
  const modalOpen = ref(false)
  // Distinct loading flags per task so a Summarize in flight does not
  // visually block Create ticket (and vice versa), and so components can
  // choose which spinner to show.
  const recapping = ref(false)
  const drafting = ref(false)
  const submitting = ref(false)
  const draft = ref<TicketDraft | null>(null)
  const result = ref<CreateIssueResponse | null>(null)
  const error = ref<string | null>(null)
  // Element to return focus to when the modal closes (a11y).
  const triggerEl = ref<HTMLElement | null>(null)

  // POST /api/helpdesk/summarize: narrative recap for inline display.
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

  // POST /api/helpdesk/draft-ticket: structured draft for the review
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

  function openModal(trigger?: HTMLElement | null): void {
    triggerEl.value = trigger ?? null
    modalOpen.value = true
  }

  function closeModal(): void {
    modalOpen.value = false
    const trigger = triggerEl.value
    triggerEl.value = null
    if (trigger && typeof trigger.focus === 'function') {
      setTimeout(() => trigger.focus(), 0)
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
    draft,
    result,
    error,
    triggerEl,
    recap,
    makeDraft,
    openModal,
    closeModal,
    submitIssue,
    reset,
  }
})
