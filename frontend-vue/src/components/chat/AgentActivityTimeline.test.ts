import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import AgentActivityTimeline from './AgentActivityTimeline.vue'
import type { AgentStep } from '@/types/helpdesk'

const STEPS: AgentStep[] = [
  { step: 'classifier', action: 'classify_ticket', outcome: 'success', message: null },
  { step: 'retrieval', action: 'retry_kb', outcome: 'success', message: '4 candidate(s)' },
  { step: 'supervisor', action: 'kb_low_confidence', outcome: 'skipped', message: 'top_score=0.18 < floor=0.40' },
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
    // The agent's KB retry is labeled distinctly from the chat-level KB
    // retrieval so users can tell the two passes apart.
    expect(screen.getByText('Knowledge base (agent retry)')).toBeTruthy()
    expect(screen.getByText('4 candidate(s)')).toBeTruthy()
    expect(screen.getByText('KB hits below confidence floor')).toBeTruthy()
    expect(screen.getByText('top_score=0.18 < floor=0.40')).toBeTruthy()
    expect(screen.getByText('Public web search')).toBeTruthy()
    expect(screen.getByText('rate-limited')).toBeTruthy()
    expect(screen.getByText('Proposed a solution')).toBeTruthy()
  })

  it('collapses by default and expands on toggle', async () => {
    const user = userEvent.setup()
    render(AgentActivityTimeline, { props: { steps: STEPS } })

    const toggle = screen.getByRole('button', { name: /What the agent did \(5\)/ })
    expect(toggle.getAttribute('aria-expanded')).toBe('false')

    await user.click(toggle)
    expect(toggle.getAttribute('aria-expanded')).toBe('true')
    expect(screen.getByText('Classified the issue')).toBeTruthy()
  })

  it('exposes the raw step/action/outcome tuple via title for power users', () => {
    render(AgentActivityTimeline, { props: { steps: STEPS, defaultExpanded: true } })
    const list = screen.getByTestId('agent-activity-timeline').querySelector('ol')!
    const items = Array.from(list.querySelectorAll('li'))
    expect(items[0].getAttribute('title')).toContain('classifier')
    expect(items[0].getAttribute('title')).toContain('classify_ticket')
    const webSearchRow = items.find((li) => li.getAttribute('title')?.includes('web_search'))
    expect(webSearchRow).toBeTruthy()
    expect(webSearchRow!.getAttribute('title')).toContain('failed')
  })
})
