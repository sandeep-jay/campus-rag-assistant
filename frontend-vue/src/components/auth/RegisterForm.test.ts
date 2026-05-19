import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '@/test/utils'
import RegisterForm from './RegisterForm.vue'
import { server } from '@/mocks/server'
import { http, HttpResponse } from 'msw'

const BASE = 'http://localhost:8000'

describe('RegisterForm', () => {
  it('renders username, email, and password fields', () => {
    renderWithProviders(RegisterForm)
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
  })

  it('has a create account button', () => {
    renderWithProviders(RegisterForm)
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument()
  })

  it('shows success message after successful registration', async () => {
    const user = userEvent.setup()
    renderWithProviders(RegisterForm)
    await user.type(screen.getByLabelText(/username/i), 'newuser')
    await user.type(screen.getByLabelText(/email/i), 'new@example.com')
    await user.type(screen.getByLabelText(/password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /create account/i }))
    await waitFor(() => {
      expect(screen.getByText(/account created/i)).toBeInTheDocument()
    })
  })

  it('shows role=alert on registration error', async () => {
    server.use(
      http.post(`${BASE}/api/auth/register`, () =>
        HttpResponse.json({ detail: 'Username already registered' }, { status: 400 }),
      ),
    )
    const user = userEvent.setup()
    renderWithProviders(RegisterForm)
    await user.type(screen.getByLabelText(/username/i), 'existing')
    await user.type(screen.getByLabelText(/email/i), 'e@e.com')
    await user.type(screen.getByLabelText(/password/i), 'pass123')
    await user.click(screen.getByRole('button', { name: /create account/i }))
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })
})
