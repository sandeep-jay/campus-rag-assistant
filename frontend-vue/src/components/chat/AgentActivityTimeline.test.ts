import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import AgentActivityTimeline from './AgentActivityTimeline.vue'
import type { AgentStep } from '@/types/helpdesk'

const STEPS: AgentStep[] = [
  { step: 'classifier', action: 'classify_ticket', outcome: 'success', message: null },
  { step: 'retrieval', action: 'retry_kb', outcome: 'success', message: '4 candidate(s)' },
  { step: 'researcher', action: 'web_search', outcome: 'failed', message: 'rate-limited' },
  { step: 'solver', action: 'propose_solution', outcome: 'waiting', message: null },
]

describe('AgentActivityTimeline', () => {
  it('renders nothing when no steps are provided', () => {
    render(AgentActivityTimeline, { props: { steps: [] } })
    expect(screen.queryByTestId('agent-activity-timeline')).toBeNull()
  })

  it('humanizes known actions and shows details inline', () => {
    render(AgentActivityTimeline, { props: { steps: STEPS, defaultExpanded: true } })
    expect(screen.getByText('Classified the issue')).toBeTruthy()
    expect(screen.getByText('Searched the knowledge base')).toBeTruthy()
    expect(screen.getByText('4 candidate(s)')).toBeTruthy()
    expect(screen.getByText('Ran a web search')).toBeTruthy()
    expect(screen.getByText('rate-limited')).toBeTruthy()
    expect(screen.getByText('Proposed a solution')).toBeTruthy()
  })

  it('collapses by default and expands on toggle', async () => {
    const user = userEvent.setup()
    render(AgentActivityTimeline, { props: { steps: STEPS } })

    const toggle = screen.getByRole('button', { name: /Steps \(4\)/ })
    expect(toggle.getAttribute('aria-expanded')).toBe('false')

    await user.click(toggle)
    expect(toggle.getAttribute('aria-expanded')).toBe('true')
    expect(screen.getByText('Classified the issue')).toBeTruthy()
  })

  it('exposes the raw step/action/outcome tuple via title for power users', () => {
    render(AgentActivityTimeline, { props: { steps: STEPS, defaultExpanded: true } })
    const list = screen.getByTestId('agent-activity-timeline').querySelector('ol')!
    const items = list.querySelectorAll('li')
    expect(items[0].getAttribute('title')).toContain('classifier')
    expect(items[0].getAttribute('title')).toContain('classify_ticket')
    expect(items[2].getAttribute('title')).toContain('failed')
  })
})
