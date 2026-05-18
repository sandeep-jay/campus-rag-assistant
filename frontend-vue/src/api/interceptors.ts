import type { AxiosError } from 'axios'
import { toast } from 'vue-sonner'
import client from './client'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

type ValidationErr = { loc?: (string | number)[]; msg?: string }

const UNAUTH_REDIRECT_COOLDOWN_MS = 3000
let lastUnauthorizedHandledAt = 0
let unauthorizedHandlingInFlight = false

function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null
  const prefix = `${name}=`
  const target = document.cookie
    .split(';')
    .map((part) => part.trim())
    .find((part) => part.startsWith(prefix))
  return target ? decodeURIComponent(target.slice(prefix.length)) : null
}

function formatApiDetail(
  detail: unknown,
  status?: number,
): string {
  if (detail == null) {
    return 'Something went wrong. Please try again.'
  }
  if (typeof detail === 'string') {
    return detail
  }
  if (Array.isArray(detail)) {
    const parts = (detail as ValidationErr[])
      .map((e) => {
        const where = Array.isArray(e.loc) ? e.loc.filter((x) => x !== 'body').join('.') : ''
        const msg = e.msg ?? 'Invalid value'
        return where ? `${where}: ${msg}` : msg
      })
      .filter(Boolean)
    if (parts.length) return parts.join(' ')
  }
  if (typeof detail === 'object' && detail !== null && 'msg' in detail) {
    return String((detail as { msg: string }).msg)
  }
  if (status && status >= 500) {
    return 'Something went wrong. Please try again.'
  }
  return 'Something went wrong. Please try again.'
}

function shouldHandleUnauthorizedNow(): boolean {
  const now = Date.now()
  if (unauthorizedHandlingInFlight) return false
  if (now - lastUnauthorizedHandledAt < UNAUTH_REDIRECT_COOLDOWN_MS) return false
  unauthorizedHandlingInFlight = true
  lastUnauthorizedHandledAt = now
  return true
}

function finishUnauthorizedHandling(): void {
  unauthorizedHandlingInFlight = false
}

/** 401 on login/register is invalid credentials or validation — not an expired session. */
function isUnauthorizedOnCredentialEndpoint(error: AxiosError): boolean {
  if (error.response?.status !== 401) return false
  const url = error.config?.url ?? ''
  const path = url.split('?')[0] ?? ''
  return (
    path.endsWith('/api/auth/login-json') ||
    path.endsWith('/api/auth/register')
  )
}

export function setupInterceptors(): void {
  client.interceptors.request.use((config) => {
    config.headers = config.headers ?? {}
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      config.headers['X-Request-ID'] = crypto.randomUUID()
    }
    const method = (config.method ?? 'get').toLowerCase()
    const isStateChanging = ['post', 'put', 'patch', 'delete'].includes(method)
    if (isStateChanging) {
      const csrfToken = getCookie('csrf_token')
      if (csrfToken) {
        config.headers = config.headers ?? {}
        config.headers['X-CSRF-Token'] = csrfToken
      }
    }
    return config
  })

  client.interceptors.response.use(
    (res) => res,
    (err: unknown) => {
      const axiosErr = err as AxiosError<{ detail?: unknown }>
      const status = axiosErr.response?.status
      const detail = axiosErr.response?.data?.detail

      if (
        status === 401 &&
        !isUnauthorizedOnCredentialEndpoint(axiosErr) &&
        shouldHandleUnauthorizedNow()
      ) {
        const authStore = useAuthStore()
        authStore.clear()
        toast.error('Your session has expired. Please sign in again.')
        router.push('/login').finally(() => {
          finishUnauthorizedHandling()
        })
      }

      const message = formatApiDetail(detail, status)
      return Promise.reject(new Error(message))
    },
  )
}
