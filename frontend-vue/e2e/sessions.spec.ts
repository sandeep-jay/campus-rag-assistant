import type { Page } from '@playwright/test'
import { test, expect } from './fixtures'

async function ensureSidebarOpen(page: Page, isMobile: boolean): Promise<void> {
  const sidebar = page.locator('aside[aria-label="Chat history"]')

  if (await sidebar.isVisible().catch(() => false)) {
    return
  }

  const toggle = page.getByRole('button', { name: /toggle sidebar/i })

  if (isMobile) {
    await toggle.click({ timeout: 5000 })
  } else {
    const hasVisibleToggle = await toggle.isVisible().catch(() => false)
    if (hasVisibleToggle) {
      await toggle.click({ timeout: 5000 })
    }
  }

  await expect(sidebar).toBeVisible()
}

test.describe('Session management', () => {
  test('sidebar shows session history nav', async ({ authedPage, isMobile }) => {
    await authedPage.goto('/chat')
    await ensureSidebarOpen(authedPage, isMobile)
    const sidebar = authedPage.locator('aside[aria-label="Chat history"]')
    await expect(sidebar).toBeVisible()
    await expect(sidebar.getByRole('navigation', { name: /sessions/i })).toBeVisible()
  })

  test('new conversation button is accessible', async ({ authedPage, isMobile }) => {
    await authedPage.goto('/chat')
    await ensureSidebarOpen(authedPage, isMobile)
    const sidebar = authedPage.locator('aside[aria-label="Chat history"]')
    await expect(
      sidebar.getByRole('button', { name: /start new conversation/i }),
    ).toBeVisible()
  })
})
