import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useChatStore } from '@/stores/chat'
import { server } from '@/mocks/server'
import { http, HttpResponse } from 'msw'

const BASE = 'http://localhost:8000'

describe('useChat (via store)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('sendMessage() optimistically pushes user message before API responds', async () => {
    const store = useChatStore()
    store.activeSessionId = 1
    const promise = store.sendMessage('Hello')
    expect(store.messages.some((m) => m.content === 'Hello')).toBe(true)
    expect(store.messages.some((m) => 'isOptimistic' in m)).toBe(true)
    await promise
  })

  it('sendMessage() rolls back optimistic message on API error', async () => {
    server.use(
      http.post(`${BASE}/api/chat/chat`, () => new HttpResponse(null, { status: 500 })),
    )
    const store = useChatStore()
    store.activeSessionId = 1
    await expect(store.sendMessage('Hello')).rejects.toThrow()
    expect(store.messages.every((m) => !('isOptimistic' in m))).toBe(true)
    expect(store.messages.length).toBe(0)
  })

  it('sendMessage() resolves successfully and adds assistant message', async () => {
    const store = useChatStore()
    store.activeSessionId = 1
    await store.sendMessage('Hello')
    expect(store.messages.some((m) => m.role === 'assistant')).toBe(true)
  })

  it('stores route.params.sessionId change loading', async () => {
    const store = useChatStore()
    await store.loadSession(1)
    expect(store.activeSessionId).toBe(1)
    expect(store.messages.length).toBeGreaterThan(0)
  })

  it('stores activeSessionId from send response without fetchSessions fallback', async () => {
    const store = useChatStore()
    // No active session — a new session must be created
    await store.sendMessage('Hello')
    expect(store.activeSessionId).toBe(1)
  })
})
