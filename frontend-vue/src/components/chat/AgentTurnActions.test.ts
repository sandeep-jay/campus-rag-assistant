import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '@/test/utils'
import AgentTurnActions from './AgentTurnActions.vue'
import { useChatStore } from '@/stores/chat'
import { useHelpdeskStore } from '@/stores/helpdesk'

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
  resumeAgentSession: vi.fn(async () => ({
    session_id: 'agent-1',
    kind: 'resolved',
    message: 'Great — I marked this helpdesk session as resolved. No ticket was filed.',
    choices: null,
    draft: null,
    linked_issue_url: null,
    debug_trace: [{ step: 'resume', action: 'solution_feedback', outcome: 'accepted', message: 'solution-agent-1' }],
  })),
}))

const turn = {
  session_id: 'agent-1',
  kind: 'info' as const,
  message: 'Here is a fix.',
  choices: ['Yes, that solved it', "Tried it, didn't work"],
  draft: null,
  linked_issue_url: null,
  debug_trace: [{ step: 'supervisor', action: 'propose_solution', outcome: 'waiting', message: 'solution-agent-1' }],
}

describe('AgentTurnActions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('resumes the agent with the clicked choice and appends the next turn', async () => {
    const api = await import('@/api/helpdesk')
    renderWithProviders(AgentTurnActions, { props: { turn } })
    const chat = useChatStore()
    const user = userEvent.setup()

    await user.click(screen.getByRole('button', { name: /yes, that solved it/i }))

    await waitFor(() => expect(api.streamResumeAgentSession).toHaveBeenCalledTimes(1))
    expect(api.streamResumeAgentSession).toHaveBeenCalledWith({
      session_id: 'agent-1',
      chat_session_id: null,
      choice: 'Yes, that solved it',
      pending_question_id: 'solution-agent-1',
    }, expect.any(Function), expect.any(Function))
    expect(chat.messages.some((m) => m.role === 'user' && m.content === 'Yes, that solved it')).toBe(true)
    expect(chat.messages.some((m) => m.role === 'assistant' && m.content.includes('resolved'))).toBe(true)
  })

  it('appends the new agent bubble BELOW the user reply (not upserted in place)', async () => {
    // Repro: the original bug was that the next agent turn replaced the
    // existing bubble at its old position (above the user's just-added
    // reply), making the new question invisible at the bottom of the
    // scroll. We assert order: prior agent bubble → user reply → new
    // agent bubble, so the user sees the next question right after their
    // answer.
    renderWithProviders(AgentTurnActions, { props: { turn } })
    const chat = useChatStore()
    chat.addAssistantMessage('Did this solve the issue?', { agent_turn: turn })
    expect(chat.messages).toHaveLength(1)

    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /yes, that solved it/i }))

    await waitFor(() => expect(chat.messages).toHaveLength(3))
    const [priorAgent, userReply, newAgent] = chat.messages
    expect(priorAgent.role).toBe('assistant')
    expect(priorAgent.content).toBe('Did this solve the issue?')
    expect(userReply.role).toBe('user')
    expect(userReply.content).toBe('Yes, that solved it')
    expect(newAgent.role).toBe('assistant')
    expect(newAgent.content).toContain('resolved')
  })

  it('renders an AskCard + radio group for radio input and submits on click', async () => {
    const api = await import('@/api/helpdesk')
    const radioTurn = {
      session_id: 'agent-1',
      kind: 'question' as const,
      message: 'Is this affecting only you, your team, or the whole campus?',
      choices: ['Only me', 'My team', 'Campus-wide', 'Not sure'],
      input: 'radio' as const,
      draft: null,
      linked_issue_url: null,
      debug_trace: [
        { step: 'clarifier', action: 'ask_user', outcome: 'waiting', message: 'impact-agent-1' },
      ],
    }
    vi.mocked(api.streamResumeAgentSession).mockResolvedValueOnce({
      session_id: 'agent-1',
      kind: 'info',
      message: 'Here is a fix.',
      choices: ['Yes, that solved it', "Tried it, didn't work"],
      draft: null,
      linked_issue_url: null,
      debug_trace: [
        { step: 'supervisor', action: 'propose_solution', outcome: 'waiting', message: 'solution-agent-1' },
      ],
    })
    renderWithProviders(AgentTurnActions, { props: { turn: radioTurn } })
    const user = userEvent.setup()

    // AskCard wrapper renders with a radiogroup and a Submit button.
    const radiogroup = await screen.findByRole('radiogroup')
    expect(radiogroup).toBeTruthy()
    const submit = screen.getByRole('button', { name: /submit/i })
    expect(submit).toBeDisabled()

    // Picking a radio enables Submit; clicking Submit resumes the agent
    // with the chosen value (confirm-before-submit, not auto-submit).
    await user.click(screen.getByRole('radio', { name: /my team/i }))
    expect(submit).not.toBeDisabled()
    await user.click(submit)

    await waitFor(() => expect(api.streamResumeAgentSession).toHaveBeenCalledTimes(1))
    expect(api.streamResumeAgentSession).toHaveBeenCalledWith({
      session_id: 'agent-1',
      chat_session_id: null,
      choice: 'My team',
      pending_question_id: 'impact-agent-1',
    }, expect.any(Function), expect.any(Function))
  })

  it('posts web-search consent through resume and appends the next turn below the user reply', async () => {
    const api = await import('@/api/helpdesk')
    const consentTurn = {
      session_id: 'agent-1',
      kind: 'question' as const,
      message: 'The knowledge base did not have a likely fix. Search the public web for troubleshooting ideas?',
      choices: ['Search the web', 'Skip and draft a ticket'],
      input: 'radio' as const,
      draft: null,
      linked_issue_url: null,
      debug_trace: [
        { step: 'supervisor', action: 'web_search_consent', outcome: 'waiting', message: 'web-consent-agent-1' },
      ],
    }
    vi.mocked(api.streamResumeAgentSession).mockResolvedValueOnce({
      session_id: 'agent-1',
      kind: 'info',
      message: 'Try clearing your browser cache and re-uploading the assignment.',
      choices: ['Yes, that solved it', "Tried it, didn't work"],
      source_kind: 'web',
      disclaimer: 'This answer used public web search results.',
      draft: null,
      linked_issue_url: null,
      debug_trace: [
        { step: 'supervisor', action: 'propose_solution', outcome: 'waiting', message: 'solution-agent-1' },
      ],
    })
    renderWithProviders(AgentTurnActions, { props: { turn: consentTurn } })
    const chat = useChatStore()
    chat.addAssistantMessage(consentTurn.message, { agent_turn: consentTurn })
    const user = userEvent.setup()

    await user.click(screen.getByRole('radio', { name: /search the web/i }))
    await user.click(screen.getByRole('button', { name: /submit/i }))

    await waitFor(() => expect(api.streamResumeAgentSession).toHaveBeenCalledTimes(1))
    expect(api.streamResumeAgentSession).toHaveBeenCalledWith({
      session_id: 'agent-1',
      chat_session_id: null,
      choice: 'Search the web',
      pending_question_id: 'web-consent-agent-1',
    }, expect.any(Function), expect.any(Function))
    await waitFor(() => expect(chat.messages).toHaveLength(3))
    const [, userReply, nextAgent] = chat.messages
    expect(userReply.role).toBe('user')
    expect(userReply.content).toBe('Search the web')
    expect(nextAgent.role).toBe('assistant')
    expect(nextAgent.content).toContain('browser cache')
  })

  it('opens the ticket modal when resume returns a draft', async () => {
    const api = await import('@/api/helpdesk')
    vi.mocked(api.streamResumeAgentSession).mockResolvedValueOnce({
      session_id: 'agent-1',
      kind: 'draft_ready',
      message: 'Review this draft.',
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
    })
    renderWithProviders(AgentTurnActions, { props: { turn } })
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /tried it/i }))
    await waitFor(() => expect(useHelpdeskStore().modalOpen).toBe(true))
    expect(useHelpdeskStore().draft?.title).toBe('Oracle Financials 403')
  })
})
