import { describe, it, expect } from 'vitest'
import { isSafeUrl } from './url'

describe('isSafeUrl', () => {
  it('accepts https:// URLs', () => {
    expect(isSafeUrl('https://example.com')).toBe(true)
  })

  it('accepts http:// URLs', () => {
    expect(isSafeUrl('http://example.com')).toBe(true)
  })

  it('accepts URLs with paths and query strings', () => {
    expect(isSafeUrl('https://kb.example.com/article?id=123')).toBe(true)
  })

  it('rejects javascript: protocol', () => {
    expect(isSafeUrl('javascript:alert(1)')).toBe(false)
  })

  it('rejects data: URIs', () => {
    expect(isSafeUrl('data:text/html,<h1>x</h1>')).toBe(false)
  })

  it('rejects empty string', () => {
    expect(isSafeUrl('')).toBe(false)
  })

  it('rejects vbscript: protocol', () => {
    expect(isSafeUrl('vbscript:msgbox(1)')).toBe(false)
  })

  it('rejects # anchor only', () => {
    expect(isSafeUrl('#')).toBe(false)
  })

  it('rejects relative paths', () => {
    expect(isSafeUrl('/foo/bar')).toBe(false)
  })
})
