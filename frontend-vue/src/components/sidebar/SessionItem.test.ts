import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '@/test/utils'
import SessionItem from './SessionItem.vue'
import type { ChatSession } from '@/api/types'

const mockSession: ChatSession = { id: 1, title: 'My Test Chat', created_at: new Date().toISOString() }

describe('SessionItem', () => {
  it('renders session title as a <button> (not a div)', () => {
    renderWithProviders(SessionItem, { props: { session: mockSession, isActive: false } })
    expect(screen.getByRole('button', { name: 'My Test Chat' })).toBeInTheDocument()
  })

  it('emits select event when title button is clicked', async () => {
    const user = userEvent.setup()
    const { emitted } = renderWithProviders(SessionItem, { props: { session: mockSession, isActive: false } })
    await user.click(screen.getByRole('button', { name: 'My Test Chat' }))
    expect(emitted('select')?.[0]).toEqual([1])
  })

  it('emits requestDelete event when delete button is clicked', async () => {
    const user = userEvent.setup()
    const { emitted } = renderWithProviders(SessionItem, { props: { session: mockSession, isActive: false } })
    await user.click(screen.getByRole('button', { name: /delete/i }))
    expect(emitted('requestDelete')?.[0]).toEqual([1])
  })
})
