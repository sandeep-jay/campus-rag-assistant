import { test, expect } from './fixtures'

test.describe('Chat', () => {
  test('chat page renders message log region', async ({ authedPage }) => {
    await authedPage.goto('/chat')
    await expect(authedPage.getByRole('log')).toBeVisible()
  })

  test('navigating to /chat/:id loads the session', async ({ authedPage }) => {
    await authedPage.goto('/chat/1')
    await expect(authedPage.getByRole('log')).toBeVisible()
  })

  test('focus returns to textarea after sending a message', async ({ authedPage }) => {
    await authedPage.goto('/chat/1')
    const textarea = authedPage.getByRole('textbox')
    await textarea.fill('What is BCourses?')
    await authedPage.keyboard.press('Enter')
    await authedPage.waitForTimeout(500)
    await expect(textarea).toBeFocused()
  })

  test('Shift+Enter inserts newline instead of submitting', async ({ authedPage }) => {
    await authedPage.goto('/chat')
    const textarea = authedPage.getByRole('textbox')
    await textarea.fill('Line 1')
    await authedPage.keyboard.press('Shift+Enter')
    const value = await textarea.inputValue()
    expect(value).toContain('\n')
  })
})
