import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '@/test/utils'
import HelpdeskActions from './HelpdeskActions.vue'
import { useChatStore } from '@/stores/chat'
import { useHelpdeskStore } from '@/stores/helpdesk'
import type { ChatMessage } from '@/api/types'

vi.mock('@/api/helpdesk', () => ({
  recapConversation: vi.fn(async () => ({
    summary:
      'The user reported an Oracle Financials 403.\n\n- KB returned no answer.\n- No remediation steps proposed.',
  })),
  draftTicket: vi.fn(async () => ({
    title: 'Oracle Financials 403',
    description: 'Budget reports return 403.',
    severity: 'high',
    category: 'application',
    steps_to_reproduce: null,
    impact: 'Team',
  })),
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

const baseMessages: ChatMessage[] = [
  { id: 1, content: 'Oracle Financials 403', role: 'user', created_at: '2024-01-01T10:00:00Z' },
  {
    id: 2,
    content: "I couldn't find information.",
    role: 'assistant',
    metadata: { kb_resolved: false, sources: [], document_contents: [] },
    created_at: '2024-01-01T10:00:01Z',
  },
]

function renderActions(): void {
  renderWithProviders(HelpdeskActions)
  useChatStore().messages = [...baseMessages]
}

describe('HelpdeskActions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders summarize and create ticket buttons', () => {
    renderActions()
    expect(screen.getByTestId('helpdesk-actions')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /summarize issue/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create ticket/i })).toBeInTheDocument()
  })

  it('summarize posts a narrative recap, not a ticket-shaped preview', async () => {
    const api = await import('@/api/helpdesk')
    renderActions()
    const chat = useChatStore()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /summarize issue/i }))
    expect(api.recapConversation).toHaveBeenCalledTimes(1)
    expect(api.draftTicket).not.toHaveBeenCalled()
    const lastMessage = chat.messages[chat.messages.length - 1]
    expect(lastMessage.role).toBe('assistant')
    expect(lastMessage.content).toContain('Conversation recap')
    // The recap must NOT include ticket fields like Severity/Category.
    expect(lastMessage.content).not.toMatch(/severity/i)
    expect(lastMessage.content).not.toMatch(/category/i)
  })

  it('leaves create ticket actionable after summarize click', async () => {
    renderActions()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /summarize issue/i }))
    expect(await screen.findByRole('button', { name: /summary added/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /create ticket/i })).toBeEnabled()
  })

  it('get help starts the agent, appends a question, and emits telemetry', async () => {
    const api = await import('@/api/helpdesk')
    const events: string[] = []
    const handler = (event: Event): void => {
      events.push((event as CustomEvent).detail.eventName)
    }
    window.addEventListener('campus-rag:telemetry', handler)
    renderActions()
    const chat = useChatStore()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /get help/i }))
    window.removeEventListener('campus-rag:telemetry', handler)
    expect(api.streamStartAgentSession).toHaveBeenCalledTimes(1)
    expect(events).toContain('helpdesk_agent_start_requested')
    expect(events).toContain('helpdesk_agent_start_completed')
    const lastMessage = chat.messages[chat.messages.length - 1]
    expect(lastMessage.role).toBe('assistant')
    expect(lastMessage.content).toContain('affecting')
    expect('metadata' in lastMessage ? lastMessage.metadata?.agent_turn?.kind : undefined).toBe('question')
  })

  it('create ticket calls draft-ticket and opens the modal', async () => {
    const api = await import('@/api/helpdesk')
    renderActions()
    const helpdesk = useHelpdeskStore()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /create ticket/i }))
    expect(api.draftTicket).toHaveBeenCalledTimes(1)
    expect(api.recapConversation).not.toHaveBeenCalled()
    expect(helpdesk.modalOpen).toBe(true)
    expect(helpdesk.draft?.title).toBe('Oracle Financials 403')
  })

  it('summarize and create ticket are independent calls', async () => {
    const api = await import('@/api/helpdesk')
    renderActions()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /summarize issue/i }))
    await screen.findByRole('button', { name: /summary added/i })
    await user.click(screen.getByRole('button', { name: /create ticket/i }))
    // Each action hits its own endpoint, in addition to its own purpose.
    expect(api.recapConversation).toHaveBeenCalledTimes(1)
    expect(api.draftTicket).toHaveBeenCalledTimes(1)
    expect(useHelpdeskStore().modalOpen).toBe(true)
  })
})
