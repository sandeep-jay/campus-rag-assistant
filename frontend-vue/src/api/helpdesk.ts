import client from './client'
import type {
  ConversationSummary,
  ConversationTurn,
  CreateIssueResponse,
  TicketDraft,
} from '@/types/helpdesk'

// Narrative conversation recap for inline display. Distinct from a
// ticket draft: the response is a free-form markdown summary.
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
