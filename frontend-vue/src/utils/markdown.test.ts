import { describe, it, expect } from 'vitest'
import { renderMarkdown } from './markdown'

describe('renderMarkdown', () => {
  it('renders basic markdown bold to <strong>', () => {
    const result = renderMarkdown('**bold** text')
    expect(result).toContain('<strong>bold</strong>')
  })

  it('strips <script> tags entirely from output', () => {
    const result = renderMarkdown('<script>alert(1)</script>')
    expect(result).not.toMatch(/<script/i)
  })

  it('strips onerror attributes from img tags', () => {
    const result = renderMarkdown('<img src="x" onerror="alert(1)">')
    expect(result).not.toContain('onerror')
  })

  it('does not create anchor elements with javascript: href', () => {
    // markdown-it refuses to render javascript: links as <a> elements
    // DOMPurify removes any href attributes anyway
    const result = renderMarkdown('[click me](javascript:alert(1))')
    expect(result).not.toContain('href=')
  })

  it('strips onclick event handlers', () => {
    const result = renderMarkdown('<div onclick="steal()">text</div>')
    expect(result).not.toContain('onclick')
  })

  it('strips iframe tags', () => {
    const result = renderMarkdown('<iframe src="https://evil.com"></iframe>')
    expect(result).not.toMatch(/<iframe/i)
  })

  it('strips style attributes', () => {
    const result = renderMarkdown('<p style="color:red">text</p>')
    expect(result).not.toContain('style=')
  })

  it('renders fenced JS code block with hljs class', () => {
    const result = renderMarkdown('```javascript\nconsole.log("hello")\n```')
    expect(result).toContain('hljs')
    expect(result).toContain('<pre>')
    expect(result).toContain('<code')
  })

  it('renders fenced Python code block with language class', () => {
    const result = renderMarkdown('```python\nprint("hello")\n```')
    expect(result).toContain('language-python')
  })

  it('renders inline code', () => {
    const result = renderMarkdown('Use `console.log()` for debugging')
    expect(result).toContain('<code>')
  })

  it('renders unordered lists', () => {
    const result = renderMarkdown('- item one\n- item two')
    expect(result).toContain('<ul>')
    expect(result).toContain('<li>')
  })

  it('renders blockquotes', () => {
    const result = renderMarkdown('> This is a quote')
    expect(result).toContain('<blockquote>')
  })

  it('allows class attributes on code elements for hljs', () => {
    const result = renderMarkdown('```js\nconst x = 1\n```')
    expect(result).toContain('class=')
  })

  it('returns a string without throwing on garbage input', () => {
    expect(() => renderMarkdown('<<<<<< weird >>>>> \x00 \uFFFD')).not.toThrow()
  })
})
