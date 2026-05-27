import client from './client'
import type {
  AgentStreamEvent,
  AgentTurn,
  ConversationSummary,
  ConversationTurn,
  CreateIssueResponse,
  TicketDraft,
} from '@/types/helpdesk'

// Narrative conversation recap for inline display. Distinct from a
// ticket draft — the response is a free-form markdown summary.
export async function recapConversation(
  conversation: ConversationTurn[],
): Promise<ConversationSummary> {
  const { data } = await client.post<{ summary: ConversationSummary }>(
    '/api/helpdesk/summarize',
    { conversation },
  )
  return data.summary
}

// Structured ticket extraction used by the Create ticket flow. The
// response is the schema the modal renders for review.
export async function draftTicket(
  conversation: ConversationTurn[],
): Promise<TicketDraft> {
  const { data } = await client.post<{ draft: TicketDraft }>(
    '/api/helpdesk/draft-ticket',
    { conversation },
  )
  return data.draft
}

export async function createIssue(
  draft: TicketDraft,
): Promise<CreateIssueResponse> {
  const { data } = await client.post<CreateIssueResponse>(
    '/api/helpdesk/create-issue',
    { draft },
  )
  return data
}

export async function startAgentSession(
  conversation: ConversationTurn[],
  chat_session_id?: number | null,
): Promise<AgentTurn> {
  const { data } = await client.post<AgentTurn>(
    '/api/helpdesk/agent/start',
    { conversation, chat_session_id: chat_session_id ?? null },
  )
  return data
}

export async function resumeAgentSession(params: {
  session_id: string
  reply?: string
  choice?: string
  pending_question_id?: string
  chat_session_id?: number | null
}): Promise<AgentTurn> {
  const { data } = await client.post<AgentTurn>(
    '/api/helpdesk/agent/resume',
    params,
  )
  return data
}


export async function abortAgentSession(
  session_id: string,
  chat_session_id?: number | null,
): Promise<AgentTurn> {
  const { data } = await client.post<AgentTurn>(
    '/api/helpdesk/agent/abort',
    { session_id, chat_session_id: chat_session_id ?? null },
  )
  return data
}


export async function confirmAgentSession(
  session_id: string,
  draft: TicketDraft,
  chat_session_id?: number | null,
): Promise<AgentTurn> {
  const { data } = await client.post<AgentTurn>(
    '/api/helpdesk/agent/confirm',
    { session_id, draft, chat_session_id: chat_session_id ?? null },
  )
  return data
}


async function streamAgentTurn(
  url: string,
  payload: unknown,
  onStatus?: (message: string) => void,
): Promise<AgentTurn> {
  const csrfCookie = document.cookie
    .split('; ')
    .find((row) => row.startsWith('csrf_token='))
    ?.split('=')[1]

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(csrfCookie ? { 'X-CSRF-Token': csrfCookie } : {}),
    },
    credentials: 'include',
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const body = await response.text().catch(() => '')
    throw new Error(`Agent stream request failed: ${response.status} ${body}`)
  }

  const reader = response.body?.getReader()
  if (!reader) throw new Error('Response body is not readable')

  const decoder = new TextDecoder()
  let buffer = ''
  let finalTurn: AgentTurn | null = null
  let streamError: string | null = null

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      buffer = lines.pop() ?? ''
      for (const line of lines) {
        const dataLine = line.trim()
        if (!dataLine.startsWith('data: ')) continue
        const rawJson = dataLine.slice(6).trim()
        if (!rawJson) continue
        const event = JSON.parse(rawJson) as AgentStreamEvent
        if (event.type === 'status') {
          onStatus?.(event.message)
        } else if (event.type === 'done') {
          finalTurn = event.turn
        } else if (event.type === 'error') {
          streamError = event.message
        }
      }
    }
  } finally {
    reader.releaseLock()
  }

  if (streamError) throw new Error(streamError)
  if (!finalTurn) throw new Error('Agent stream ended without a final turn')
  return finalTurn
}

export async function streamStartAgentSession(
  conversation: ConversationTurn[],
  chat_session_id?: number | null,
  onStatus?: (message: string) => void,
): Promise<AgentTurn> {
  return streamAgentTurn(
    '/api/helpdesk/agent/start/stream',
    { conversation, chat_session_id: chat_session_id ?? null },
    onStatus,
  )
}

export async function streamResumeAgentSession(params: {
  session_id: string
  reply?: string
  choice?: string
  pending_question_id?: string
  chat_session_id?: number | null
}, onStatus?: (message: string) => void): Promise<AgentTurn> {
  return streamAgentTurn('/api/helpdesk/agent/resume/stream', params, onStatus)
}
