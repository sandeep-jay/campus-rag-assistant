import client from './client'
import type {
  ChatSession,
  ChatSessionCreate,
  SessionWithMessages,
  SendMessageResponse,
  FeedbackCreate,
  FeedbackResponse,
  MessageSourcesResponse,
  StreamEvent,
  ResearchMode,
} from './types'

export async function getSessions(): Promise<ChatSession[]> {
  const { data } = await client.get<ChatSession[]>('/api/chat/sessions')
  return data
}

export async function createSession(payload: ChatSessionCreate): Promise<ChatSession> {
  const { data } = await client.post<ChatSession>('/api/chat/sessions', payload)
  return data
}

export async function getSession(sessionId: number): Promise<SessionWithMessages> {
  const { data } = await client.get<SessionWithMessages>(`/api/chat/sessions/${sessionId}`)
  return data
}

export async function deleteSession(sessionId: number): Promise<void> {
  await client.delete(`/api/chat/sessions/${sessionId}`)
}

export async function sendMessage(
  content: string,
  sessionId?: number | null,
  researchMode: ResearchMode = 'kb',
): Promise<SendMessageResponse> {
  const { data } = await client.post<SendMessageResponse>('/api/chat/chat', {
    content,
    session_id: sessionId ?? undefined,
    research_mode: researchMode,
  })
  return data
}

/**
 * Stream a chat response via SSE.
 *
 * Calls the POST /api/chat/stream endpoint and invokes callbacks for each
 * token and for the final "done" event (which carries sources and session_id).
 *
 * Uses fetch() directly because Axios does not support streaming and
 * EventSource does not support POST requests.
 */
export async function streamMessage(
  content: string,
  sessionId: number | null | undefined,
  onToken: (token: string) => void,
  onDone: (event: Extract<StreamEvent, { type: 'done' }>) => void,
  onError?: (message: string) => void,
  onStatus?: (message: string) => void,
  researchMode: ResearchMode = 'kb',
  signal?: AbortSignal,
): Promise<void> {
  const csrfCookie = document.cookie
    .split('; ')
    .find((row) => row.startsWith('csrf_token='))
    ?.split('=')[1]

  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(csrfCookie ? { 'X-CSRF-Token': csrfCookie } : {}),
    },
    credentials: 'include',
    body: JSON.stringify({
      content,
      session_id: sessionId ?? undefined,
      research_mode: researchMode,
    }),
    signal,
  })

  if (!response.ok) {
    const body = await response.text().catch(() => '')
    throw new Error(`Stream request failed: ${response.status} ${body}`)
  }

  const reader = response.body?.getReader()
  if (!reader) throw new Error('Response body is not readable')

  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // SSE lines are separated by double newlines
      const lines = buffer.split('\n\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        const dataLine = line.trim()
        if (!dataLine.startsWith('data: ')) continue
        const rawJson = dataLine.slice(6).trim()
        if (!rawJson) continue

        try {
          const event = JSON.parse(rawJson) as StreamEvent
          if (event.type === 'status') {
            onStatus?.(event.message)
          } else if (event.type === 'token') {
            onToken(event.token)
          } else if (event.type === 'done') {
            onDone(event)
          } else if (event.type === 'error') {
            onError?.(event.message ?? 'An error occurred during streaming.')
          }
        } catch {
          // Malformed JSON line — skip
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

export async function submitFeedback(payload: FeedbackCreate): Promise<FeedbackResponse> {
  const { data } = await client.post<FeedbackResponse>('/api/chat/feedback', payload)
  return data
}

export async function getMessageSources(messageId: number): Promise<MessageSourcesResponse> {
  const { data } = await client.get<MessageSourcesResponse>(
    `/api/chat/messages/${messageId}/sources`,
  )
  return data
}
