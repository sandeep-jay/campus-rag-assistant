import AxeBuilder from '@axe-core/playwright'
import { test, expect } from './fixtures'

test.describe('Accessibility (axe WCAG scans)', () => {
  test('login page has no critical axe violations', async ({ page }) => {
    await page.goto('/login')
    await page.waitForLoadState('networkidle')
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze()
    expect(results.violations).toEqual([])
  })

  test('chat page has no critical axe violations', async ({ authedPage }) => {
    await authedPage.goto('/chat')
    await authedPage.waitForLoadState('networkidle')
    const results = await new AxeBuilder({ page: authedPage })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze()
    expect(results.violations).toEqual([])
  })
})
