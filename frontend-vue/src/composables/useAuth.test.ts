import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuth } from './useAuth'

describe('useAuth', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('exposes isAuthenticated as false initially', () => {
    const { isAuthenticated } = useAuth()
    expect(isAuthenticated.value).toBe(false)
  })

  it('exposes user as null initially', () => {
    const { user } = useAuth()
    expect(user.value).toBeNull()
  })

  it('exposes login, logout, clear functions', () => {
    const { login, logout, clear } = useAuth()
    expect(typeof login).toBe('function')
    expect(typeof logout).toBe('function')
    expect(typeof clear).toBe('function')
  })

  it('login() updates isAuthenticated to true on success', async () => {
    const { login, isAuthenticated } = useAuth()
    await login({ username: 'testuser', password: 'pass' })
    expect(isAuthenticated.value).toBe(true)
  })

  it('clear() resets user to null', async () => {
    const { login, clear, isAuthenticated } = useAuth()
    await login({ username: 'testuser', password: 'pass' })
    clear()
    expect(isAuthenticated.value).toBe(false)
  })
})
