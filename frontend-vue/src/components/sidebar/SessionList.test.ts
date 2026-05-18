import { describe, it, expect } from 'vitest'
import { screen, waitFor, within } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '@/test/utils'
import SessionList from './SessionList.vue'
import type { ChatSession } from '@/api/types'

const today = new Date().toISOString()
const yesterday = new Date(Date.now() - 86400000).toISOString()
const lastWeek = new Date(Date.now() - 8 * 86400000).toISOString()

const mockSessions: ChatSession[] = [
  { id: 1, title: 'Recent Chat Today', created_at: today },
  { id: 2, title: 'Chat From Yesterday', created_at: yesterday },
  { id: 3, title: 'Old Chat Last Week', created_at: lastWeek },
]

describe('SessionList', () => {
  it('renders inside a <nav> element with accessible label', () => {
    renderWithProviders(SessionList, { props: { sessions: mockSessions, activeSessionId: null } })
    const nav = screen.getByRole('navigation', { name: /sessions/i })
    expect(nav).toBeInTheDocument()
  })

  it('renders session titles as buttons (via aria-label)', () => {
    renderWithProviders(SessionList, { props: { sessions: mockSessions, activeSessionId: null } })
    expect(screen.getByRole('button', { name: 'Recent Chat Today' })).toBeInTheDocument()
  })

  it('groups sessions under Today / Yesterday / Older headings', () => {
    renderWithProviders(SessionList, { props: { sessions: mockSessions, activeSessionId: null } })
    expect(screen.getByText('Today')).toBeInTheDocument()
    expect(screen.getByText('Yesterday')).toBeInTheDocument()
    expect(screen.getByText('Older')).toBeInTheDocument()
  })

  it('shows empty state when no sessions', () => {
    renderWithProviders(SessionList, { props: { sessions: [], activeSessionId: null } })
    expect(screen.getByText(/no conversations/i)).toBeInTheDocument()
  })

  it('emits select event when a session is clicked', async () => {
    const { emitted } = renderWithProviders(SessionList, { props: { sessions: mockSessions, activeSessionId: null } })
    await screen.getByRole('button', { name: 'Recent Chat Today' }).click()
    expect(emitted('select')?.[0]).toEqual([1])
  })

  it('shows one centralized delete confirmation and emits delete on confirm', async () => {
    const user = userEvent.setup()
    const { emitted } = renderWithProviders(SessionList, { props: { sessions: mockSessions, activeSessionId: null } })

    await user.click(screen.getByRole('button', { name: /Delete: Recent Chat Today/i }))
    await waitFor(() => {
      const dialog = screen.getByRole('dialog')
      expect(dialog).toBeInTheDocument()
      expect(within(dialog).getByText('Recent Chat Today')).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: 'Delete' }))
    expect(emitted('delete')?.[0]).toEqual([1])
  })
})
