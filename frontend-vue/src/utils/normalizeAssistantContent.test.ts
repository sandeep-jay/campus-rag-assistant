import { describe, it, expect } from 'vitest'
import { normalizeAssistantContent } from './normalizeAssistantContent'

describe('normalizeAssistantContent', () => {
  it('breaks inline numbered lists onto separate lines', () => {
    const result = normalizeAssistantContent('Intro 1. First 2. Second')
    expect(result).toContain('\n1. First')
    expect(result).toContain('\n2. Second')
  })

  it('strips kb_url leakage lines', () => {
    const result = normalizeAssistantContent('Answer text\nkb_url: https://example.com/kb/1')
    expect(result).toBe('Answer text')
    expect(result).not.toContain('kb_url')
  })

  it('promotes standalone bold titles to headings', () => {
    const result = normalizeAssistantContent('**Group Management**\n- item')
    expect(result).toContain('## Group Management')
  })

  it('strips condensed question before em-dash answer', () => {
    const raw =
      'How do I submit an assignment in the learning platform?— Students can submit assignments in bCourses.'
    const result = normalizeAssistantContent(raw)
    expect(result).not.toMatch(/^How do I submit/)
    expect(result).toContain('Students can submit')
  })
})
