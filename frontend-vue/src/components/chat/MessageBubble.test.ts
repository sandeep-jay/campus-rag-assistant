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

  it('applies assistant row background tint; user row does not', () => {
    const { container, unmount } = renderWithProviders(MessageBubble, { props: { message: assistantMessage } })
    const assistantRow = container.querySelector('[data-testid="assistant-bubble"]') as HTMLElement | null
    expect(assistantRow).toBeTruthy()
    expect(assistantRow!.className).toContain('bg-muted/20')
    unmount()

    const { container: c2 } = renderWithProviders(MessageBubble, { props: { message: userMessage } })
    const userRow = c2.querySelector('[data-testid="user-bubble"]') as HTMLElement | null
    expect(userRow).toBeTruthy()
    expect(userRow!.className).not.toContain('bg-muted/20')
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

  it('does NOT show feedback buttons for user messages', () => {
    renderWithProviders(MessageBubble, { props: { message: userMessage } })
    expect(screen.queryByRole('button', { name: /mark as helpful/i })).not.toBeInTheDocument()
  })
})
