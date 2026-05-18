import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useChatStore } from './chat'
import { server } from '@/mocks/server'
import { http, HttpResponse } from 'msw'

const BASE = 'http://localhost:8000'

describe('useChatStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('starts with empty state', () => {
    const store = useChatStore()
    expect(store.sessions).toEqual([])
    expect(store.activeSessionId).toBeNull()
    expect(store.messages).toEqual([])
  })

  it('fetchSessions() loads sessions from API', async () => {
    const store = useChatStore()
    await store.fetchSessions()
    expect(store.sessions.length).toBeGreaterThan(0)
    expect(store.sessions[0].id).toBe(1)
  })

  it('loadSession() loads messages for a session', async () => {
    const store = useChatStore()
    await store.loadSession(1)
    expect(store.activeSessionId).toBe(1)
    expect(store.messages.length).toBeGreaterThan(0)
  })

  it('sendMessage() optimistically adds user bubble before API resolves', async () => {
    const store = useChatStore()
    store.activeSessionId = 1
    const promise = store.sendMessage('Hello')
    expect(store.messages.some((m) => m.content === 'Hello')).toBe(true)
    expect(store.messages.some((m) => 'isOptimistic' in m)).toBe(true)
    await promise
  })

  it('sendMessage() replaces optimistic bubble with real messages on success', async () => {
    const store = useChatStore()
    store.activeSessionId = 1
    await store.sendMessage('Hello')
    const hasOptimistic = store.messages.some((m) => 'isOptimistic' in m)
    expect(hasOptimistic).toBe(false)
    expect(store.messages.some((m) => m.role === 'assistant')).toBe(true)
  })

  it('sendMessage() records retryable content on transient failure', async () => {
    server.use(
      http.post(`${BASE}/api/chat/chat`, () => new HttpResponse(null, { status: 500 })),
    )
    const store = useChatStore()
    store.activeSessionId = 1
    await expect(store.sendMessage('Hello')).rejects.toThrow()
    expect(store.messages.length).toBe(0)
    expect(store.retryableSendContent).toBe('Hello')
  })

  it('retryLastFailedSend() re-sends last failed message and clears retry state', async () => {
    const store = useChatStore()
    store.retryableSendContent = 'Retry this'
    await store.retryLastFailedSend()
    expect(store.retryableSendContent).toBeNull()
    expect(store.messages.some((m) => m.role === 'assistant')).toBe(true)
  })

  it('sendMessage() uses response session_id and avoids full sessions refetch', async () => {
    const store = useChatStore()
    const fetchSpy = vi.spyOn(store, 'fetchSessions')
    await store.sendMessage('new session message')
    expect(store.activeSessionId).toBe(1)
    expect(store.sessions.some((s) => s.id === 1)).toBe(true)
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('deleteSession() removes session and clears active if deleted', async () => {
    const store = useChatStore()
    await store.fetchSessions()
    store.activeSessionId = 1
    await store.deleteSession(1)
    expect(store.sessions.find((s) => s.id === 1)).toBeUndefined()
    expect(store.activeSessionId).toBeNull()
  })

  it('startNewChat() clears activeSessionId and messages', () => {
    const store = useChatStore()
    store.activeSessionId = 1
    store.messages = [{ id: 1, content: 'hi', role: 'user', created_at: '' }]
    store.retryableSendContent = 'retry'
    store.startNewChat()
    expect(store.activeSessionId).toBeNull()
    expect(store.messages).toEqual([])
    expect(store.retryableSendContent).toBeNull()
  })

  it('clear() resets all state', async () => {
    const store = useChatStore()
    await store.fetchSessions()
    store.retryableSendContent = 'retry'
    store.clear()
    expect(store.sessions).toEqual([])
    expect(store.activeSessionId).toBeNull()
    expect(store.retryableSendContent).toBeNull()
  })
})
