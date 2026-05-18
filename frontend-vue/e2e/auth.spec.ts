import { test, expect } from './fixtures'

test.describe('Authentication', () => {
  test('skip link is the first focusable element on login page', async ({ page, isMobile }) => {
    await page.goto('/login')

    if (isMobile) {
      await expect(page.getByRole('link', { name: /skip to main content/i })).toHaveCount(1)
      return
    }

    await page.keyboard.press('Tab')
    const focused = page.locator(':focus')
    await expect(focused).toHaveText(/skip to main content/i)
  })

  test('unauthenticated user is redirected to /login', async ({ browser }) => {
    const ctx = await browser.newContext() // no storageState
    const page = await ctx.newPage()
    await page.goto('/chat')
    await expect(page).toHaveURL(/\/login/)
    await ctx.close()
  })

  test('authenticated user can access /chat', async ({ authedPage }) => {
    await authedPage.goto('/chat')
    await expect(authedPage).toHaveURL(/\/chat/)
    await expect(authedPage.getByRole('main')).toBeVisible()
  })

  test('user can log out', async ({ authedPage }) => {
    await authedPage.goto('/chat')
    const userMenuBtn = authedPage.getByRole('button', { name: /user menu/i })
    await userMenuBtn.click()
    await authedPage.getByRole('menuitem', { name: /log out/i }).click()
    await expect(authedPage).toHaveURL(/\/login/)
  })
})
