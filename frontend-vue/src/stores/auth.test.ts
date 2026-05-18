import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from './auth'
import { server } from '@/mocks/server'
import { http, HttpResponse } from 'msw'

const BASE = 'http://localhost:8000'

describe('useAuthStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('isAuthenticated is false initially', () => {
    const store = useAuthStore()
    expect(store.isAuthenticated).toBe(false)
    expect(store.user).toBeNull()
  })

  it('login() sets user in store', async () => {
    const store = useAuthStore()
    await store.login({ username: 'testuser', password: 'pass' })
    expect(store.user?.username).toBe('testuser')
    expect(store.user?.id).toBe(1)
    expect(store.isAuthenticated).toBe(true)
  })

  it('login() clears error on start', async () => {
    const store = useAuthStore()
    store.error = 'previous error'
    await store.login({ username: 'testuser', password: 'pass' })
    expect(store.error).toBeNull()
  })

  it('clear() resets user to null', async () => {
    const store = useAuthStore()
    await store.login({ username: 'testuser', password: 'pass' })
    store.clear()
    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
  })

  it('logout() calls API and clears user', async () => {
    const store = useAuthStore()
    store.user = { id: 1, username: 'testuser', email: 'test@test.com' }
    await store.logout()
    expect(store.user).toBeNull()
  })

  it('login() throws on 401 and does not set user', async () => {
    server.use(
      http.post(`${BASE}/api/auth/login-json`, () => new HttpResponse(null, { status: 401 })),
    )
    const store = useAuthStore()
    await expect(store.login({ username: 'wrong', password: 'bad' })).rejects.toThrow()
    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
  })

  it('fetchCurrentUser() populates user from /me', async () => {
    const store = useAuthStore()
    await store.fetchCurrentUser()
    expect(store.user?.username).toBe('testuser')
    expect(store.user?.email).toBe('test@test.com')
  })

  it('fetchCurrentUser() sets user to null on 401', async () => {
    server.use(
      http.get(`${BASE}/api/auth/me`, () => new HttpResponse(null, { status: 401 })),
    )
    const store = useAuthStore()
    await store.fetchCurrentUser()
    expect(store.user).toBeNull()
  })
})
