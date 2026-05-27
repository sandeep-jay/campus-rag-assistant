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
    expect(api.recapConversation).toHaveBeenCalledTimes(1)
    expect(api.draftTicket).toHaveBeenCalledTimes(1)
    expect(useHelpdeskStore().modalOpen).toBe(true)
  })
})
