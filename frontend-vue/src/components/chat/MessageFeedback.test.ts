import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '@/test/utils'
import MessageFeedback from './MessageFeedback.vue'
import { server } from '@/mocks/server'
import { http, HttpResponse } from 'msw'

const BASE = 'http://localhost:8000'

describe('MessageFeedback', () => {
  it('thumbs-up button has aria-label="Mark as helpful"', () => {
    renderWithProviders(MessageFeedback, { props: { messageId: 2 } })
    expect(screen.getByRole('button', { name: 'Mark as helpful' })).toBeInTheDocument()
  })

  it('thumbs-down button has aria-label="Mark as not helpful"', () => {
    renderWithProviders(MessageFeedback, { props: { messageId: 2 } })
    expect(screen.getByRole('button', { name: 'Mark as not helpful' })).toBeInTheDocument()
  })

  it('POSTs feedback_type="thumbs_up" (not "positive") on thumbs-up click', async () => {
    let requestBody: Record<string, unknown> = {}
    server.use(
      http.post(`${BASE}/api/chat/feedback`, async ({ request }) => {
        requestBody = (await request.json()) as Record<string, unknown>
        return HttpResponse.json({ id: 1, message_id: 2, feedback_type: 'thumbs_up' })
      }),
    )
    const user = userEvent.setup()
    renderWithProviders(MessageFeedback, { props: { messageId: 2 } })
    await user.click(screen.getByRole('button', { name: 'Mark as helpful' }))
    await waitFor(() => {
      expect(requestBody.feedback_type).toBe('thumbs_up')
      expect(requestBody.message_id).toBe(2)
    })
  })

  it('POSTs feedback_type="thumbs_down" on thumbs-down click', async () => {
    let requestBody: Record<string, unknown> = {}
    server.use(
      http.post(`${BASE}/api/chat/feedback`, async ({ request }) => {
        requestBody = (await request.json()) as Record<string, unknown>
        return HttpResponse.json({ id: 1, message_id: 2, feedback_type: 'thumbs_down' })
      }),
    )
    const user = userEvent.setup()
    renderWithProviders(MessageFeedback, { props: { messageId: 2 } })
    await user.click(screen.getByRole('button', { name: 'Mark as not helpful' }))
    await waitFor(() => {
      expect(requestBody.feedback_type).toBe('thumbs_down')
    })
  })

  it('disables both buttons after feedback is submitted', async () => {
    const user = userEvent.setup()
    renderWithProviders(MessageFeedback, { props: { messageId: 2 } })
    await user.click(screen.getByRole('button', { name: 'Mark as helpful' }))
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Mark as helpful' })).toBeDisabled()
      expect(screen.getByRole('button', { name: 'Mark as not helpful' })).toBeDisabled()
    })
  })
})
