import { describe, it, expect, beforeEach } from 'vitest'
import { isDark, useDarkMode } from './useDarkMode'
import { nextTick } from 'vue'

describe('useDarkMode', () => {
  beforeEach(() => {
    // Reset module-level singleton state between tests
    isDark.value = false
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
  })

  it('isDark starts as false when no preference is stored', () => {
    expect(isDark.value).toBe(false)
  })

  it('toggle() switches isDark from false to true', async () => {
    const { toggle } = useDarkMode()
    expect(isDark.value).toBe(false)
    toggle()
    await nextTick()
    expect(isDark.value).toBe(true)
  })

  it('toggle() switches isDark from true to false', async () => {
    isDark.value = true
    const { toggle } = useDarkMode()
    toggle()
    await nextTick()
    expect(isDark.value).toBe(false)
  })

  it('sets data-theme="dark" on html element when isDark is true', async () => {
    isDark.value = true
    useDarkMode()
    await nextTick()
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
  })

  it('sets data-theme="light" on html element when isDark is false', async () => {
    isDark.value = false
    useDarkMode()
    await nextTick()
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
  })

  it('persists theme choice to localStorage on toggle', async () => {
    const { toggle } = useDarkMode()
    toggle()
    await nextTick()
    expect(localStorage.getItem('theme')).toBe('dark')
    toggle()
    await nextTick()
    expect(localStorage.getItem('theme')).toBe('light')
  })
})
