import { mkdirSync } from 'node:fs'
import { chromium, request, type FullConfig } from '@playwright/test'

const AUTH_DIR = 'e2e/.auth'
const AUTH_FILE = `${AUTH_DIR}/user.json`
const RUN_ID = `${Date.now()}-${Math.floor(Math.random() * 1e6)}`
const USERNAME = `e2e_user_${RUN_ID}`
const PASSWORD = 'testpass123!'
const EMAIL = `${USERNAME}@example.com`

async function waitForHealthyApi(apiBaseUrl: string, timeoutMs = 120_000): Promise<void> {
  const deadline = Date.now() + timeoutMs
  const api = await request.newContext({ baseURL: apiBaseUrl })
  try {
    while (Date.now() < deadline) {
      try {
        const res = await api.get('/api/health')
        if (res.ok()) return
      } catch {
        /* API not listening yet */
      }
      await new Promise((r) => setTimeout(r, 500))
    }
    throw new Error(`Timed out waiting for ${apiBaseUrl}/api/health (${timeoutMs}ms)`)
  } finally {
    await api.dispose()
  }
}

async function registerUser(apiBaseUrl: string): Promise<void> {
  const api = await request.newContext({ baseURL: apiBaseUrl })
  try {
    const registerRes = await api.post('/api/auth/register', {
      data: { username: USERNAME, email: EMAIL, password: PASSWORD },
    })

    if (!registerRes.ok()) {
      let detail = ''
      try {
        const body = (await registerRes.json()) as { detail?: unknown }
        detail = String(body?.detail ?? JSON.stringify(body))
      } catch {
        detail = await registerRes.text()
      }
      throw new Error(`User registration failed (${registerRes.status()}): ${detail}`)
    }
  } finally {
    await api.dispose()
  }
}

export default async function globalSetup(config: FullConfig): Promise<void> {
  const baseUrl = String(config.projects[0]?.use?.baseURL ?? 'http://localhost:5173')
  const apiBaseUrl = process.env.PLAYWRIGHT_API_BASE_URL ?? 'http://127.0.0.1:8000'

  await waitForHealthyApi(apiBaseUrl)

  mkdirSync(AUTH_DIR, { recursive: true })
  await registerUser(apiBaseUrl)

  const browser = await chromium.launch()
  const page = await browser.newPage()

  try {
    await page.goto(`${baseUrl}/login`)
    await page.locator('#login-username').fill(USERNAME)
    await page.locator('#login-password').fill(PASSWORD)
    await page.getByRole('button', { name: /sign in/i }).click()
    await page.waitForURL('**/chat', { timeout: 20000 })
    await page.context().storageState({ path: AUTH_FILE })
  } finally {
    await browser.close()
  }
}
