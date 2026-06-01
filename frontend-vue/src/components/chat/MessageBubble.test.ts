import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '@/test/utils'
import MessageBubble from './MessageBubble.vue'
import type { ChatMessage } from '@/api/types'

const userMessage: ChatMessage = {
  id: 1, content: 'Hello there', role: 'user', created_at: '2024-01-01T10:00:00Z',
}

const assistantMessage: ChatMessage = {
  id: 2,
  content: '**Bold response** with `code`',
  role: 'assistant',
  metadata: { sources: [], document_contents: [] },
  created_at: '2024-01-01T10:00:01Z',
}

const assistantWithSources: ChatMessage = {
  id: 99,
  content: 'Answer with refs',
  role: 'assistant',
  metadata: {
    sources: [
      {
        kb_url: 'https://kb.example.com/x',
        kb_number: 'KB-1',
        kb_category: 'C',
        short_description: 'S1',
        project: 'P',
      },
      {
        kb_url: 'https://kb.example.com/y',
        kb_number: 'KB-2',
        kb_category: 'C',
        short_description: 'S2',
        project: 'P',
      },
    ],
    document_contents: [],
  },
  created_at: '2024-01-01T10:00:00Z',
}

describe('MessageBubble', () => {
  it('renders user message content', () => {
    renderWithProviders(MessageBubble, { props: { message: userMessage } })
    expect(screen.getByText('Hello there')).toBeInTheDocument()
  })

  it('renders assistant message with markdown (bold)', () => {
    renderWithProviders(MessageBubble, { props: { message: assistantMessage } })
    expect(document.querySelector('strong')).toBeInTheDocument()
  })

  it('sanitizes XSS script tags in assistant content', () => {
    const xssMessage: ChatMessage = {
      id: 3,
      content: '<script>alert("xss")</script>Hello',
      role: 'assistant',
      created_at: '',
    }
    renderWithProviders(MessageBubble, { props: { message: xssMessage } })
    expect(document.querySelector('script')).toBeNull()
  })

  it('sanitizes onerror XSS in assistant content', () => {
    const xssMessage: ChatMessage = {
      id: 4,
      content: '<img src="x" onerror="alert(1)">',
      role: 'assistant',
      created_at: '',
    }
    renderWithProviders(MessageBubble, { props: { message: xssMessage } })
    const imgs = document.querySelectorAll('img')
    imgs.forEach((img) => expect(img.getAttribute('onerror')).toBeNull())
  })

  it('renders code block with hljs class for assistant messages', () => {
    const codeMessage: ChatMessage = {
      id: 5,
      content: '```javascript\nconsole.log("test")\n```',
      role: 'assistant',
      created_at: '',
    }
    renderWithProviders(MessageBubble, { props: { message: codeMessage } })
    expect(document.querySelector('.hljs')).toBeInTheDocument()
  })

  it('shows copy button on assistant messages', () => {
    renderWithProviders(MessageBubble, { props: { message: assistantMessage } })
    expect(screen.getByRole('button', { name: /copy message/i })).toBeInTheDocument()
  })

  it('shows feedback buttons for assistant messages', () => {
    renderWithProviders(MessageBubble, { props: { message: assistantMessage } })
    expect(screen.getByRole('button', { name: /mark as helpful/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /mark as not helpful/i })).toBeInTheDocument()
  })

  it('collapses sources by default: summary visible, panel tabs absent', () => {
    renderWithProviders(MessageBubble, { props: { message: assistantWithSources } })
    expect(screen.getByTestId('sources-summary')).toBeInTheDocument()
    expect(screen.queryByTestId('sources-panel')).not.toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: 'Sources' })).not.toBeInTheDocument()
  })

  it('expands SourcesPanel when summary toggle is clicked', async () => {
    const user = userEvent.setup()
    renderWithProviders(MessageBubble, { props: { message: assistantWithSources } })
    await user.click(screen.getByRole('button', { name: /Sources \(2\)/i }))
    expect(screen.getByTestId('sources-panel')).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Sources' })).toBeInTheDocument()
  })

  it('keeps assistant and user rows transparent; the bubble carries the visual weight', () => {
    const assistantMsg: ChatMessage = {
      id: 7,
      role: 'assistant',
      content: 'A',
      created_at: new Date().toISOString(),
      metadata: null,
    }
    const userMsg: ChatMessage = {
      id: 8,
      role: 'user',
      content: 'B',
      created_at: new Date().toISOString(),
      metadata: null,
    }
    let { container, unmount } = renderWithProviders(MessageBubble, { props: { message: assistantMsg } })
    const assistantRow = container.querySelector('[data-testid="assistant-bubble"]')
    expect(assistantRow).toBeTruthy()
    // Tokens-v2: the row is transparent; the assistant bubble (bg-card)
    // does the layering against the cool off-white page background.
    expect(assistantRow!.className).not.toContain('bg-muted')
    unmount()
    ;({ container, unmount } = renderWithProviders(MessageBubble, { props: { message: userMsg } }))
    const userRow = container.querySelector('[data-testid="user-bubble"]')
    expect(userRow).toBeTruthy()
    expect(userRow!.className).not.toContain('bg-muted')
    unmount()
  })

  it('shows web disclaimer when metadata.disclaimer is set', () => {
    const webMessage: ChatMessage = {
      id: 6,
      content: 'Web answer',
      role: 'assistant',
      metadata: {
        disclaimer: 'This answer used public web search results. Verify against official sources.',
        source_kind: 'web',
        sources: [],
        document_contents: [],
      },
      created_at: '',
    }
    renderWithProviders(MessageBubble, { props: { message: webMessage } })
    expect(screen.getByTestId('web-disclaimer')).toHaveTextContent(/public web search/i)
  })


  it('shows helpdesk actions when kb_resolved is false and isLastMessage', () => {
    const unresolved: ChatMessage = {
      id: 7,
      content: "I couldn't find information.",
      role: 'assistant',
      metadata: { kb_resolved: false, sources: [], document_contents: [] },
      created_at: '',
    }
    renderWithProviders(MessageBubble, {
      props: { message: unresolved, isLastMessage: true },
    })
    expect(screen.getByTestId('helpdesk-actions')).toBeInTheDocument()
  })

  it('hides helpdesk actions when kb_resolved is true', () => {
    const resolved: ChatMessage = {
      id: 8,
      content: 'Here is how to submit an assignment.',
      role: 'assistant',
      metadata: { kb_resolved: true, sources: [], document_contents: [] },
      created_at: '',
    }
    renderWithProviders(MessageBubble, {
      props: { message: resolved, isLastMessage: true },
    })
    expect(screen.queryByTestId('helpdesk-actions')).not.toBeInTheDocument()
  })

  it('shows helpdesk actions when router classifies turn as helpdesk above floor', () => {
    const routerEscalated: ChatMessage = {
      id: 9,
      content: 'Here is general info...',
      role: 'assistant',
      metadata: {
        kb_resolved: true,
        sources: [],
        document_contents: [],
        router_decision: { domain: 'helpdesk', confidence: 0.85, reason: 'router' },
      },
      created_at: '',
    }
    renderWithProviders(MessageBubble, {
      props: { message: routerEscalated, isLastMessage: true },
    })
    expect(screen.getByTestId('helpdesk-actions')).toBeInTheDocument()
  })

  it('hides helpdesk actions when router classifies helpdesk below floor', () => {
    const routerWeak: ChatMessage = {
      id: 10,
      content: 'Here is general info...',
      role: 'assistant',
      metadata: {
        kb_resolved: true,
        sources: [],
        document_contents: [],
        router_decision: { domain: 'helpdesk', confidence: 0.4, reason: 'low' },
      },
      created_at: '',
    }
    renderWithProviders(MessageBubble, {
      props: { message: routerWeak, isLastMessage: true },
    })
    expect(screen.queryByTestId('helpdesk-actions')).not.toBeInTheDocument()
  })

  it('does NOT show feedback buttons for user messages', () => {
    renderWithProviders(MessageBubble, { props: { message: userMessage } })
    expect(screen.queryByRole('button', { name: /mark as helpful/i })).not.toBeInTheDocument()
  })

  // Multi-turn helpdesk-agent bubbles: only the bottom-most agent bubble is
  // the active turn. Older bubbles in the same agent session keep their
  // question text and timeline but must not re-render the interactive
  // pills/radios that the user has already answered — otherwise scrolling
  // up shows ghost buttons that can fire stale resume calls.
  const agentQuestionTurn = {
    session_id: 'agent-1',
    kind: 'question' as const,
    message: 'Did this solve the issue?',
    choices: ['Yes, that solved it', "No, doesn't apply", "Tried it, didn't work"],
    input: 'pills' as const,
    draft: null,
    linked_issue_url: null,
    debug_trace: [{ step: 'supervisor', action: 'propose_solution', outcome: 'waiting', message: 'solution-agent-1' }],
  }
  const agentBubble: ChatMessage = {
    id: 11,
    content: 'Did this solve the issue?',
    role: 'assistant',
    metadata: { agent_turn: agentQuestionTurn, sources: [], document_contents: [] },
    created_at: '2024-01-01T10:00:00Z',
  }

  it('renders AgentTurnActions on the bottom-most agent bubble (isLastMessage)', () => {
    renderWithProviders(MessageBubble, {
      props: { message: agentBubble, isLastMessage: true },
    })
    expect(screen.getByTestId('agent-turn-actions')).toBeInTheDocument()
  })

  it('hides AgentTurnActions on older agent bubbles (not isLastMessage)', () => {
    renderWithProviders(MessageBubble, {
      props: { message: agentBubble, isLastMessage: false },
    })
    expect(screen.queryByTestId('agent-turn-actions')).not.toBeInTheDocument()
  })
})
