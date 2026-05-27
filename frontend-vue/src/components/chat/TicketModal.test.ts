import { describe, it, expect, vi, beforeEach } from 'vitest'
import { nextTick } from 'vue'
import { screen, waitFor } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '@/test/utils'
import TicketModal from './TicketModal.vue'
import { useHelpdeskStore } from '@/stores/helpdesk'
import { useChatStore } from '@/stores/chat'
import { confirmAgentSession, createIssue } from '@/api/helpdesk'

vi.mock('@/api/helpdesk', () => ({
  recapConversation: vi.fn(),
  draftTicket: vi.fn(),
  confirmAgentSession: vi.fn(async () => ({
    session_id: 'agent-1',
    kind: 'filed',
    message: 'Issue #77 was filed.\n\n[View on GitHub](https://github.com/demo-org/demo-repo/issues/77)',
    choices: null,
    draft: null,
    linked_issue_url: 'https://github.com/demo-org/demo-repo/issues/77',
    debug_trace: [{ step: 'tool', action: 'file_ticket', outcome: 'success', message: '77' }],
  })),
  createIssue: vi.fn(async () => ({
    issue_url: 'https://github.com/demo-org/demo-repo/issues/42',
    issue_number: 42,
    deduplicated: false,
  })),
  streamStartAgentSession: vi.fn(async () => ({
    session_id: 'agent-1',
    kind: 'question',
    message: 'Is this affecting only you, your team, or the whole campus?',
    choices: ['Only me', 'My team'],
    draft: null,
    linked_issue_url: null,
    debug_trace: [{ step: 'clarifier', action: 'ask_user', outcome: 'waiting', message: 'impact-agent-1' }],
  })),
  startAgentSession: vi.fn(),
  abortAgentSession: vi.fn(),
  streamResumeAgentSession: vi.fn(async () => ({
    session_id: 'agent-1',
    kind: 'resolved',
    message: 'Great — I marked this helpdesk session as resolved. No ticket was filed.',
    choices: null,
    draft: null,
    linked_issue_url: null,
    debug_trace: [{ step: 'resume', action: 'solution_feedback', outcome: 'accepted', message: 'solution-agent-1' }],
  })),
  resumeAgentSession: vi.fn(),
}))

async function openModal(): Promise<void> {
  const helpdesk = useHelpdeskStore()
  helpdesk.draft = {
    title: 'Oracle Financials 403',
    description: 'Budget reports return 403.',
    severity: 'high',
    category: 'application',
    steps_to_reproduce: null,
    impact: 'Team',
  }
  helpdesk.modalOpen = true
  await nextTick()
}

describe('TicketModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('exposes dialog semantics and sensitive-info warning', async () => {
    renderWithProviders(TicketModal)
    await openModal()
    expect(await screen.findByRole('dialog')).toBeInTheDocument()
    expect(screen.getByTestId('helpdesk-sensitive-warning')).toBeInTheDocument()
    expect(screen.getByLabelText(/^title$/i)).toHaveValue('Oracle Financials 403')
  })

  it('closes on Escape', async () => {
    renderWithProviders(TicketModal)
    await openModal()
    const helpdesk = useHelpdeskStore()
    const user = userEvent.setup()
    await user.keyboard('{Escape}')
    expect(helpdesk.modalOpen).toBe(false)
  })

  it('submits reviewed draft and resets store', async () => {
    renderWithProviders(TicketModal)
    await openModal()
    const helpdesk = useHelpdeskStore()
    const chat = useChatStore()
    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: /create issue/i }))
    await waitFor(() => expect(vi.mocked(createIssue)).toHaveBeenCalled())
    expect(helpdesk.modalOpen).toBe(false)
    expect(chat.messages.some((m) => m.role === 'assistant' && m.content.includes('#42'))).toBe(true)
  })
  it('files agent drafts through agent confirm and clears the active turn', async () => {
    renderWithProviders(TicketModal)
    await openModal()
    const helpdesk = useHelpdeskStore()
    const chat = useChatStore()
    helpdesk.recordAgentTurn({
      session_id: 'agent-1',
      kind: 'draft_ready',
      message: 'Review this draft.',
      choices: null,
      draft: helpdesk.draft,
      linked_issue_url: null,
      debug_trace: null,
    })
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: /create issue/i }))

    await waitFor(() => expect(vi.mocked(confirmAgentSession)).toHaveBeenCalled())
    expect(vi.mocked(createIssue)).not.toHaveBeenCalled()
    expect(helpdesk.modalOpen).toBe(false)
    expect(helpdesk.activeTurn).toBeNull()
    expect(chat.messages.some((m) => m.role === 'assistant' && m.content.includes('#77'))).toBe(true)
  })

})
