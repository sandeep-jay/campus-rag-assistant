import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/vue'
import { renderWithProviders } from '@/test/utils'
import SourcesPanel from './SourcesPanel.vue'
import type { Source, DocContent } from '@/api/types'

const safeSources: Source[] = [
  {
    kb_url: 'https://kb.example.com/article-123',
    kb_number: 'KB-123',
    kb_category: 'Course Management',
    short_description: 'How to submit assignments',
    project: 'BCourses',
    score: 0.92,
  },
]

const dangerousSources: Source[] = [
  {
    kb_url: 'javascript:alert(1)',
    kb_number: 'KB-BAD',
    kb_category: 'Test',
    short_description: 'Dangerous source',
    project: 'Test',
    score: 0.5,
  },
]

const safeDocContents: DocContent[] = [
  { content: 'Article content here', metadata: safeSources[0] },
]

const noScoreSources: Source[] = [
  {
    kb_url: 'https://kb.example.com/article-no-score',
    kb_number: 'KB-999',
    kb_category: 'Course Management',
    short_description: 'Source without score',
    project: 'BCourses',
  },
]

describe('SourcesPanel', () => {
  it('shows empty state when no sources', () => {
    renderWithProviders(SourcesPanel, { props: { sources: [], documentContents: [] } })
    expect(screen.getByText(/no sources/i)).toBeInTheDocument()
  })

  it('renders safe https:// source as clickable anchor', () => {
    renderWithProviders(SourcesPanel, { props: { sources: safeSources, documentContents: safeDocContents } })
    const link = document.querySelector('a[href="https://kb.example.com/article-123"]')
    expect(link).toBeInTheDocument()
  })

  it('does NOT render javascript: URL as anchor href', () => {
    renderWithProviders(SourcesPanel, { props: { sources: dangerousSources, documentContents: [] } })
    expect(document.querySelector('a[href^="javascript"]')).toBeNull()
  })

  it('renders source title and KB number', () => {
    renderWithProviders(SourcesPanel, { props: { sources: safeSources, documentContents: safeDocContents } })
    expect(screen.getByText('How to submit assignments')).toBeInTheDocument()
    expect(screen.getByText(/KB-123/)).toBeInTheDocument()
  })

  it('renders source score', () => {
    renderWithProviders(SourcesPanel, { props: { sources: safeSources, documentContents: safeDocContents } })
    expect(screen.getByText(/0\.92/)).toBeInTheDocument()
  })


  it('renders N/A when score is missing', () => {
    renderWithProviders(SourcesPanel, { props: { sources: noScoreSources, documentContents: [] } })
    expect(screen.getByText(/Score: N\/A/)).toBeInTheDocument()
  })

  it('uses rel="noopener noreferrer" on external links', () => {
    renderWithProviders(SourcesPanel, { props: { sources: safeSources, documentContents: safeDocContents } })
    const link = document.querySelector('a')
    expect(link?.getAttribute('rel')).toContain('noopener')
    expect(link?.getAttribute('rel')).toContain('noreferrer')
  })
})
