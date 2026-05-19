import { describe, it, expect, vi } from 'vitest'
import { screen } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '@/test/utils'
import ChatInput from './ChatInput.vue'

describe('ChatInput', () => {
  it('is wrapped in a <form> element', () => {
    renderWithProviders(ChatInput)
    expect(document.querySelector('form')).toBeInTheDocument()
  })

  it('has a textarea for message input', () => {
    renderWithProviders(ChatInput)
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  it('send button has aria-label="Send message"', () => {
    renderWithProviders(ChatInput)
    expect(screen.getByRole('button', { name: 'Send message' })).toBeInTheDocument()
  })

  it('emits submit event on Enter key', async () => {
    const user = userEvent.setup()
    const { emitted } = renderWithProviders(ChatInput)
    const textarea = screen.getByRole('textbox')
    await user.type(textarea, 'Hello world')
    await user.keyboard('{Enter}')
    expect(emitted('submit')).toBeTruthy()
    expect(emitted('submit')?.[0]).toEqual(['Hello world'])
  })

  it('does NOT emit submit on Shift+Enter (inserts newline)', async () => {
    const user = userEvent.setup()
    const { emitted } = renderWithProviders(ChatInput)
    const textarea = screen.getByRole('textbox')
    await user.type(textarea, 'Hello')
    await user.keyboard('{Shift>}{Enter}{/Shift}')
    expect(emitted('submit')).toBeFalsy()
  })

  it('clears input after submit', async () => {
    const user = userEvent.setup()
    renderWithProviders(ChatInput)
    const textarea = screen.getByRole('textbox')
    await user.type(textarea, 'Test message')
    await user.keyboard('{Enter}')
    expect(textarea).toHaveValue('')
  })

  it('does not emit submit when input is empty', async () => {
    const user = userEvent.setup()
    const { emitted } = renderWithProviders(ChatInput)
    await user.keyboard('{Enter}')
    expect(emitted('submit')).toBeFalsy()
  })

  it('shows web-only helper text when research mode is web', () => {
    vi.stubEnv('VITE_WEB_RESEARCH_ENABLED', 'true')
    renderWithProviders(ChatInput, { props: { researchMode: 'web' } })
    expect(screen.getByText(/public web search only/i)).toBeInTheDocument()
    vi.unstubAllEnvs()
  })

  it('disables send button when disabled prop is true', () => {
    renderWithProviders(ChatInput, { props: { disabled: true } })
    expect(screen.getByRole('button', { name: 'Send message' })).toBeDisabled()
  })
})
