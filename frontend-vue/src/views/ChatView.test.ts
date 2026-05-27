import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '@/test/utils'
import ChatView from './ChatView.vue'
import { useChatStore } from '@/stores/chat'
import { useHelpdeskStore } from '@/stores/helpdesk'

vi.mock('@/api/chat', () => ({
  getSessions: vi.fn(async () => []),
  getSession: vi.fn(),
  deleteSession: vi.fn(),
  sendMessage: vi.fn(async () => ({
    session_id: 1,
    user_message: { id: 1, content: 'hello', role: 'user', created_at: '' },
    assistant_message: { id: 2, content: 'KB answer', role: 'assistant', created_at: '', metadata: { kb_resolved: true } },
  })),
  streamMessage: vi.fn(async () => { throw new Error('stream unavailable') }),
}))

vi.mock('@/api/helpdesk', () => ({
  recapConversation: vi.fn(),
  draftTicket: vi.fn(),
  createIssue: vi.fn(),
  streamStartAgentSession: vi.fn(async () => ({
    session_id: 'agent-1',
    kind: 'question',
    message: 'Is this affecting only you, your team, or the whole campus?',
    choices: ['Only me', 'My team'],
    draft: null,
    linked_issue_url: null,
    debug_trace: [{ step: 'clarifier', action: 'ask_user', outcome: 'waiting', message: 'impact-agent-1' }],
  })),
  startAgentSession: vi.fn(async () => ({
    session_id: 'agent-1',
    kind: 'question',
    message: 'Is this affecting only you, your team, or the whole campus?',
    choices: ['Only me', 'My team'],
    draft: null,
    linked_issue_url: null,
    debug_trace: [{ step: 'clarifier', action: 'ask_user', outcome: 'waiting', message: 'impact-agent-1' }],
  })),
  abortAgentSession: vi.fn(async () => ({
    session_id: 'agent-1',
    kind: 'aborted',
    message: 'Helpdesk agent session canceled. No ticket was filed.',
    choices: null,
    draft: null,
    linked_issue_url: null,
    debug_trace: [{ step: 'supervisor', action: 'abort', outcome: 'success', message: null }],
  })),
  streamResumeAgentSession: vi.fn(async () => ({
    session_id: 'agent-1',
    kind: 'draft_ready',
    message: 'I prepared a ticket draft.',
    choices: null,
    draft: {
      title: 'Oracle Financials 403',
      description: 'Budget reports return 403.',
      severity: 'high',
      category: 'application',
      steps_to_reproduce: null,
      impact: 'Team',
    },
    linked_issue_url: null,
    debug_trace: null,
  })),
  resumeAgentSession: vi.fn(async () => ({
    session_id: 'agent-1',
    kind: 'draft_ready',
    message: 'I prepared a ticket draft.',
    choices: null,
    draft: {
      title: 'Oracle Financials 403',
      description: 'Budget reports return 403.',
      severity: 'high',
      category: 'application',
      steps_to_reproduce: null,
      impact: 'Team',
    },
    linked_issue_url: null,
    debug_trace: null,
  })),
}))

describe('ChatView agent mode', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('toggles into agent mode and starts the helpdesk agent from typed input', async () => {
    const api = await import('@/api/helpdesk')
    renderWithProviders(ChatView, { initialRoute: '/chat' })
    const user = userEvent.setup()

    const events: string[] = []
    const handler = (event: Event): void => {
      events.push((event as CustomEvent).detail.eventName)
    }
    window.addEventListener('campus-rag:telemetry', handler)

    await user.click(screen.getByRole('switch', { name: /toggle helpdesk agent mode/i }))
    expect(useChatStore().chatMode).toBe('agent')
    expect(events).toContain('helpdesk_agent_mode_changed')
    expect(screen.getByText(/replies continue the helpdesk workflow/i)).toBeInTheDocument()

    await user.type(screen.getByRole('textbox'), 'Create a ticket for Oracle 403')
    await user.keyboard('{Enter}')

    await waitFor(() => expect(api.streamStartAgentSession).toHaveBeenCalledTimes(1))
    expect(api.streamStartAgentSession).toHaveBeenCalledWith([
      { role: 'user', content: 'Create a ticket for Oracle 403' },
    ], null, expect.any(Function))
    expect(events).toContain('helpdesk_agent_start_completed')
    window.removeEventListener('campus-rag:telemetry', handler)
    expect(screen.getByText(/affecting only you/i)).toBeInTheDocument()
  })

  it('routes typed replies to /agent/resume when a turn is active', async () => {
    const api = await import('@/api/helpdesk')
    renderWithProviders(ChatView, { initialRoute: '/chat' })
    const chat = useChatStore()
    const helpdesk = useHelpdeskStore()
    chat.setChatMode('agent')
    helpdesk.recordAgentTurn({
      session_id: 'agent-1',
      kind: 'question',
      message: 'Impact?',
      choices: ['Only me', 'My team'],
      draft: null,
      linked_issue_url: null,
      debug_trace: [{ step: 'clarifier', action: 'ask_user', outcome: 'waiting', message: 'impact-agent-1' }],
    })
    const user = userEvent.setup()

    await user.type(screen.getByRole('textbox'), 'It affects my team')
    await user.keyboard('{Enter}')

    await waitFor(() => expect(api.streamResumeAgentSession).toHaveBeenCalledTimes(1))
    expect(api.streamResumeAgentSession).toHaveBeenCalledWith({
      session_id: 'agent-1',
      reply: 'It affects my team',
      pending_question_id: 'impact-agent-1',
      chat_session_id: null,
    }, expect.any(Function))
    expect(helpdesk.modalOpen).toBe(true)
    expect(helpdesk.draft?.title).toBe('Oracle Financials 403')
  })
  it('aborts the active agent session when switching back to ask mode', async () => {
    const api = await import('@/api/helpdesk')
    vi.spyOn(window, 'confirm').mockReturnValueOnce(true)
    renderWithProviders(ChatView, { initialRoute: '/chat' })
    const chat = useChatStore()
    const helpdesk = useHelpdeskStore()
    chat.setChatMode('agent')
    helpdesk.recordAgentTurn({
      session_id: 'agent-1',
      kind: 'question',
      message: 'Impact?',
      choices: ['Only me', 'My team'],
      draft: null,
      linked_issue_url: null,
      debug_trace: [{ step: 'clarifier', action: 'ask_user', outcome: 'waiting', message: 'impact-agent-1' }],
    })
    const user = userEvent.setup()

    await user.click(screen.getByRole('switch', { name: /toggle helpdesk agent mode/i }))

    await waitFor(() => expect(api.abortAgentSession).toHaveBeenCalledWith('agent-1', null))
    expect(chat.chatMode).toBe('ask')
    expect(helpdesk.activeTurn).toBeNull()
    expect(screen.getByText(/session canceled/i)).toBeInTheDocument()
  })

})
