import { nextTick } from 'vue'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '@/test/utils'
import TicketModal from './TicketModal.vue'
import { useHelpdeskStore } from '@/stores/helpdesk'
import { useChatStore } from '@/stores/chat'
import { createIssue } from '@/api/helpdesk'

vi.mock('@/api/helpdesk', () => ({
  recapConversation: vi.fn(),
  draftTicket: vi.fn(),
  createIssue: vi.fn(async () => ({
    issue_url: 'https://github.com/demo-org/demo-repo/issues/7',
    issue_number: 7,
    deduplicated: false,
  })),
}))

async function openModal(): Promise<void> {
  renderWithProviders(TicketModal)
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

  it('renders draft fields and the sensitive-info warning', async () => {
    await openModal()
    expect(screen.getByRole('dialog', { name: /review support ticket/i })).toBeInTheDocument()
    expect(screen.getByDisplayValue('Oracle Financials 403')).toBeInTheDocument()
    expect(screen.getByTestId('helpdesk-sensitive-warning')).toHaveTextContent(/remove any sensitive information/i)
  })

  it('submits the reviewed draft and appends the GitHub issue link', async () => {
    await openModal()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /^create issue$/i }))
    await waitFor(() => expect(vi.mocked(createIssue)).toHaveBeenCalledTimes(1))
    expect(useHelpdeskStore().modalOpen).toBe(false)
    const lastMessage = useChatStore().messages.at(-1)
    expect(lastMessage?.content).toContain('Issue #7 was filed')
    expect(lastMessage?.content).toContain('View on GitHub')
  })

  it('closes without submitting when cancel is clicked', async () => {
    await openModal()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /cancel/i }))
    expect(useHelpdeskStore().modalOpen).toBe(false)
    expect(createIssue).not.toHaveBeenCalled()
  })
})
