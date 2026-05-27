export type Severity = 'low' | 'medium' | 'high' | 'critical'
export type Category =
  | 'network'
  | 'access'
  | 'application'
  | 'hardware'
  | 'account'
  | 'other'
export type Impact = 'Single user' | 'Team' | 'Campus-wide'

export interface TicketDraft {
  title: string
  description: string
  severity: Severity
  category: Category
  steps_to_reproduce: string | null
  impact: Impact
}

// Narrative recap of a conversation produced by the helpdesk summarize
// endpoint. Independent of TicketDraft: Summarize emits this for inline
// display; only Create ticket produces a structured TicketDraft.
export interface ConversationSummary {
  summary: string
}

export interface CreateIssueResponse {
  issue_url: string
  issue_number: number
  deduplicated: boolean
}

export interface ConversationTurn {
  role: 'user' | 'assistant'
  content: string
}
