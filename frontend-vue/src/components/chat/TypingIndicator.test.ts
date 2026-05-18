import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/vue'
import TypingIndicator from './TypingIndicator.vue'

describe('TypingIndicator', () => {
  it('has role="status" for screen reader announcements', () => {
    render(TypingIndicator)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('has aria-live="polite"', () => {
    render(TypingIndicator)
    expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite')
  })

  it('contains sr-only text for screen readers', () => {
    render(TypingIndicator)
    expect(screen.getByText(/assistant is thinking/i)).toBeInTheDocument()
  })
})
