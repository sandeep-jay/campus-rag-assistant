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
// agent. Independent of TicketDraft — Summarize emits this for inline
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

export interface AgentStep {
  step: string
  action: string
  outcome: string
  message: string | null
  latency_ms?: number | null
}

export interface AgentSource {
  source: string
  kb_url: string
  kb_number: string
  kb_category: string
  short_description: string
  project: string
  ingestion_date?: string
  score?: number | null
}

export interface AgentDocContent {
  content: string
  metadata: AgentSource
}

export interface AgentStreamStepEvent {
  type: 'step'
  node: string
  action: string
  status: 'running' | 'success' | 'error'
  latency_ms: number | null
  summary: string | null
}

export type AgentTurnKind =
  | 'question'
  | 'info'
  | 'draft_ready'
  | 'linked'
  | 'filed'
  | 'resolved'
  | 'aborted'

export type AgentInputMode = 'pills' | 'radio' | 'checkbox' | 'text'

export interface AgentTurn {
  session_id: string
  // Server-issued chat_messages row id when the agent persists a durable
  // summary on a terminal turn (filed / linked / resolved / aborted) and
  // a chat_session_id was supplied. Used to reconcile the optimistic
  // in-memory bubble with the persisted record on reload.
  chat_message_id?: number | null
  kind: AgentTurnKind
  message: string
  choices: string[] | null
  // Optional UI hint for how `choices` should be rendered. When absent or
  // 'pills', clicking a choice auto-submits (current behavior). 'radio'
  // asks the frontend to render an accessible radio group with an explicit
  // submit button so the user can confirm or change their answer first.
  input?: AgentInputMode | null
  draft: TicketDraft | null
  linked_issue_url: string | null
  debug_trace: AgentStep[] | null
  sources?: AgentSource[] | null
  document_contents?: AgentDocContent[] | null
  source_kind?: 'kb' | 'web' | null
  disclaimer?: string | null
}

export type AgentStreamEvent =
  | { type: 'status'; message: string }
  | AgentStreamStepEvent
  | { type: 'done'; turn: AgentTurn }
  | { type: 'error'; message: string }
