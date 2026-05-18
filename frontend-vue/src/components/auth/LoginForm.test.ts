import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '@/test/utils'
import LoginForm from './LoginForm.vue'
import { server } from '@/mocks/server'
import { http, HttpResponse } from 'msw'

const BASE = 'http://localhost:8000'

describe('LoginForm', () => {
  it('renders username and password fields with labels', () => {
    renderWithProviders(LoginForm)
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
  })

  it('renders a sign in button', () => {
    renderWithProviders(LoginForm)
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('submits credentials when form is filled and submitted', async () => {
    const user = userEvent.setup()
    renderWithProviders(LoginForm)
    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/password/i), 'password')
    await user.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() => {
      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    })
  })

  it('shows role=alert error message on 401 login failure', async () => {
    server.use(
      http.post(`${BASE}/api/auth/login-json`, () =>
        HttpResponse.json({ detail: 'Incorrect credentials' }, { status: 401 }),
      ),
    )
    const user = userEvent.setup()
    renderWithProviders(LoginForm)
    await user.type(screen.getByLabelText(/username/i), 'wrong')
    await user.type(screen.getByLabelText(/password/i), 'bad')
    await user.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })

  it('button is initially disabled when fields are empty', () => {
    renderWithProviders(LoginForm)
    expect(screen.getByRole('button', { name: /sign in/i })).toBeDisabled()
  })
})
