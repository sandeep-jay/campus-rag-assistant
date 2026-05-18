import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/vue'
import { renderWithProviders } from '@/test/utils'
import MessageList from './MessageList.vue'
import type { ChatMessage } from '@/api/types'

const mockMessages: ChatMessage[] = [
  { id: 1, content: 'Hello', role: 'user', created_at: '2024-01-01T10:00:00Z' },
  { id: 2, content: 'Hi there!', role: 'assistant', metadata: { sources: [], document_contents: [] }, created_at: '2024-01-01T10:00:01Z' },
]

describe('MessageList', () => {
  it('has role="log" for screen reader live region', () => {
    renderWithProviders(MessageList, { props: { messages: [] } })
    expect(screen.getByRole('log')).toBeInTheDocument()
  })

  it('has aria-label on the log region', () => {
    renderWithProviders(MessageList, { props: { messages: [] } })
    const log = screen.getByRole('log')
    expect(log).toHaveAttribute('aria-label', 'Conversation')
  })

  it('has aria-live="polite" on the log region', () => {
    renderWithProviders(MessageList, { props: { messages: [] } })
    const log = screen.getByRole('log')
    expect(log).toHaveAttribute('aria-live', 'polite')
  })

  it('renders user and assistant messages', () => {
    renderWithProviders(MessageList, { props: { messages: mockMessages } })
    expect(screen.getByText('Hello')).toBeInTheDocument()
    expect(screen.getByText('Hi there!')).toBeInTheDocument()
  })

  it('shows empty state when no messages', () => {
    renderWithProviders(MessageList, { props: { messages: [] } })
    expect(screen.getByText(/start a new conversation/i)).toBeInTheDocument()
  })
})
