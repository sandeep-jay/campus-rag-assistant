export interface User {
  id: number
  username: string
  email: string
}

export interface LoginResponse {
  user_id: number
  username: string
  status: 'success'
}

export interface RegisterResponse {
  message: string
}

export interface Source {
  kb_url: string
  kb_number: string
  kb_category: string
  short_description: string
  project: string
  score?: number
}

export interface DocContent {
  content: string
  metadata: Source
}

export interface ChatMessage {
  id: number
  content: string
  role: 'user' | 'assistant'
  metadata?: {
    sources?: Source[]
    document_contents?: DocContent[]
    source_kind?: ResearchMode
    disclaimer?: string | null
  }
  created_at: string
}

// Optimistic message variant (no server id yet)
export interface OptimisticMessage {
  id: string // temp string id like 'opt-<uuid>'
  content: string
  role: 'user'
  isOptimistic: true
  created_at: string
}

export type DisplayMessage = ChatMessage | OptimisticMessage | StreamingMessage

export type ResearchMode = 'kb' | 'web'

export interface ChatMessageRequest {
  content: string
  session_id?: number
  research_mode?: ResearchMode
}

export interface SendMessageResponse {
  session_id: number
  user_message: ChatMessage
  assistant_message: ChatMessage
}

export interface ChatSession {
  id: number
  title: string
  created_at: string
}

export interface ChatSessionCreate {
  title: string
  tenant_id?: number
}

export interface FeedbackCreate {
  message_id: number
  // IMPORTANT: use 'thumbs_up' / 'thumbs_down', NOT 'positive' / 'negative'
  feedback_type: 'thumbs_up' | 'thumbs_down' | 'rating'
  rating?: number // 1–4; required only when feedback_type='rating'
  comment?: string
  run_id?: string // LangSmith trace ID, pass-through
}

export interface FeedbackResponse {
  id: number
  message_id: number
  user_id: number
  feedback_type: 'thumbs_up' | 'thumbs_down' | 'rating'
  rating: number | null
  comment: string | null
  run_id: string | null
  created_at: string
}

export interface SessionWithMessages extends ChatSession {
  messages: ChatMessage[]
}

export interface MessageSourcesResponse {
  message_id: number
  document_contents: DocContent[]
  sources: Source[]
}

// Server-Sent Events shapes for POST /api/chat/stream
export type StreamEvent =
  | { type: 'status'; message: string }
  | { type: 'token'; token: string }
  | {
      type: 'done'
      sources: Source[]
      document_contents: DocContent[]
      session_id: number
      source_kind?: ResearchMode
      disclaimer?: string | null
    }
  | { type: 'error'; message: string }

// Streaming message being assembled in real-time (displayed while SSE is open)
export interface StreamingMessage {
  id: 'streaming'
  content: string
  role: 'assistant'
  isStreaming: true
  created_at: string
}
