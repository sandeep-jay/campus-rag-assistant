import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '@/test/utils'
import SourcesSummary from './SourcesSummary.vue'
import type { Source } from '@/api/types'

const mkSource = (n: number, url = `https://kb.example.com/a${n}`): Source => ({
  kb_url: url,
  kb_number: `KB-${n}`,
  kb_category: 'Cat',
  short_description: `Desc ${n}`,
  project: 'P',
  score: 0.5,
})

describe('SourcesSummary', () => {
  it('renders Sources (N) toggle when sources passed', () => {
    const sources = [mkSource(1), mkSource(2), mkSource(3)]
    renderWithProviders(SourcesSummary, {
      props: { sources, expanded: false, panelId: 'sources-panel-test' },
    })
    expect(screen.getByTestId('sources-summary')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Sources \(3\)/i })).toBeInTheDocument()
  })

  it('toggle has aria-expanded false initially', () => {
    const sources = [mkSource(1)]
    renderWithProviders(SourcesSummary, {
      props: { sources, expanded: false, panelId: 'p1' },
    })
    expect(screen.getByRole('button', { name: /Sources \(1\)/i })).toHaveAttribute('aria-expanded', 'false')
  })

  it('emits toggle when toggle button clicked', async () => {
    const user = userEvent.setup()
    const sources = [mkSource(1)]
    const { emitted } = renderWithProviders(SourcesSummary, {
      props: { sources, expanded: false, panelId: 'p1' },
    })
    await user.click(screen.getByRole('button', { name: /Sources \(1\)/i }))
    expect(emitted('toggle')).toBeTruthy()
    expect(emitted('toggle')).toHaveLength(1)
  })

  it('renders up to maxChips chips and +N more when overflow', () => {
    const sources: Source[] = [1, 2, 3, 4, 5].map((n) => mkSource(n))
    renderWithProviders(SourcesSummary, {
      props: { sources, expanded: false, panelId: 'p1', maxChips: 2 },
    })
    expect(screen.getByText('KB-1')).toBeInTheDocument()
    expect(screen.getByText('KB-2')).toBeInTheDocument()
    expect(screen.queryByText('KB-3')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /\+3 more/i })).toBeInTheDocument()
  })

  it('safe URL chip is an anchor', () => {
    const sources = [mkSource(1, 'https://safe.example/x')]
    renderWithProviders(SourcesSummary, {
      props: { sources, expanded: false, panelId: 'p1' },
    })
    const link = document.querySelector('a[href="https://safe.example/x"]')
    expect(link).toBeInTheDocument()
  })

  it('unsafe URL chip is not an anchor', () => {
    const sources: Source[] = [{
      kb_url: 'javascript:alert(1)',
      kb_number: 'KB-BAD',
      kb_category: 'T',
      short_description: 'Bad',
      project: 'P',
    }]
    renderWithProviders(SourcesSummary, {
      props: { sources, expanded: false, panelId: 'p1' },
    })
    expect(document.querySelector('a[href^="javascript"]')).toBeNull()
    expect(screen.getByText('KB-BAD')).toBeInTheDocument()
  })

  it('chips have title from short_description', () => {
    const sources = [mkSource(1)]
    renderWithProviders(SourcesSummary, {
      props: { sources, expanded: false, panelId: 'p1' },
    })
    const chip = screen.getByText('KB-1').closest('a')
    expect(chip?.getAttribute('title')).toBe('Desc 1')
  })

  it('shows Content (N) when sources empty but documentContentsCount > 0', () => {
    renderWithProviders(SourcesSummary, {
      props: {
        sources: [],
        expanded: false,
        panelId: 'p1',
        documentContentsCount: 2,
      },
    })
    expect(screen.getByRole('button', { name: /Content \(2\)/i })).toBeInTheDocument()
  })

  it('renders nothing when no sources and no document count', () => {
    const { container } = renderWithProviders(SourcesSummary, {
      props: { sources: [], expanded: false, panelId: 'p1', documentContentsCount: 0 },
    })
    expect(container.querySelector('[data-testid="sources-summary"]')).toBeNull()
  })
})
