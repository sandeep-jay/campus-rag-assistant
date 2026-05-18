import { existsSync } from 'node:fs'
import { test as base, type Page } from '@playwright/test'

type Fixtures = { authedPage: Page }

const AUTH_STATE_PATH = 'e2e/.auth/user.json'

export const test = base.extend<Fixtures>({
  authedPage: async ({ browser }, use) => {
    const hasAuthState = existsSync(AUTH_STATE_PATH)
    const ctx = hasAuthState
      ? await browser.newContext({ storageState: AUTH_STATE_PATH })
      : await browser.newContext()
    const page = await ctx.newPage()
    await use(page)
    await ctx.close()
  },
})

export { expect } from '@playwright/test'
