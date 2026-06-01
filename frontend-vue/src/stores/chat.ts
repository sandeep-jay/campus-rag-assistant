import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import * as chatApi from '@/api/chat'
import type { ChatMessage, ChatSession, DisplayMessage, OptimisticMessage, StreamingMessage, ResearchMode } from '@/api/types'
import { normalizeAssistantContent } from '@/utils/normalizeAssistantContent'

export type ChatMode = 'ask' | 'agent'

function generateOptimisticId(): string {
  return `opt-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

function titleFromContent(content: string): string {
  return content.length > 40 ? `${content.slice(0, 40)}...` : content
}

export const useChatStore = defineStore('chat', () => {
  const sessions = ref<ChatSession[]>([])
  const activeSessionId = ref<number | null>(null)
  const messages = ref<DisplayMessage[]>([])
  const isLoading = ref(false)
  const isSendingMessage = ref(false)
  const sessionsLoading = ref(false)
  const retryableSendContent = ref<string | null>(null)
  const researchMode = ref<ResearchMode>('kb')
  const chatMode = ref<ChatMode>('ask')

  // Streaming state — the in-progress assistant message while SSE is open
  const streamingMessage = ref<StreamingMessage | null>(null)
  const streamingStatus = ref<string | null>(null)

  const activeSession = computed(() =>
    sessions.value.find((s) => s.id === activeSessionId.value) ?? null,
  )

  async function fetchSessions(): Promise<void> {
    sessionsLoading.value = true
    try {
      sessions.value = await chatApi.getSessions()
    } finally {
      sessionsLoading.value = false
    }
  }

  async function loadSession(sessionId: number): Promise<void> {
    if (activeSessionId.value === sessionId && messages.value.length > 0) return
    isLoading.value = true
    try {
      const session = await chatApi.getSession(sessionId)
      activeSessionId.value = sessionId
      messages.value = session.messages
      if (!sessions.value.find((s) => s.id === session.id)) {
        sessions.value = [{ id: session.id, title: session.title, created_at: session.created_at }, ...sessions.value]
      }
    } finally {
      isLoading.value = false
    }
  }

  async function deleteSession(sessionId: number): Promise<void> {
    await chatApi.deleteSession(sessionId)
    sessions.value = sessions.value.filter((s) => s.id !== sessionId)
    if (activeSessionId.value === sessionId) {
      activeSessionId.value = null
      messages.value = []
    }
  }

  function upsertSession(sessionId: number, content: string): void {
    if (sessions.value.some((s) => s.id === sessionId)) return
    sessions.value = [
      {
        id: sessionId,
        title: titleFromContent(content),
        created_at: new Date().toISOString(),
      },
      ...sessions.value,
    ]
  }

  /**
   * Send a message using SSE streaming (POST /api/chat/stream).
   * Falls back to the non-streaming endpoint if streaming fails or is unavailable.
   */
  async function sendMessage(content: string): Promise<void> {
    retryableSendContent.value = null
    const optimisticId = generateOptimisticId()
    const optimistic: OptimisticMessage = {
      id: optimisticId,
      content,
      role: 'user',
      isOptimistic: true,
      created_at: new Date().toISOString(),
    }
    messages.value = [...messages.value, optimistic]
    isSendingMessage.value = true

    // Start with an empty streaming placeholder so the UI can show a live cursor
    streamingStatus.value = null
    streamingMessage.value = {
      id: 'streaming',
      content: '',
      role: 'assistant',
      isStreaming: true,
      created_at: new Date().toISOString(),
    }

    const appendToken = (token: string): void => {
      if (!streamingMessage.value) return
      streamingMessage.value = {
        ...streamingMessage.value,
        content: streamingMessage.value.content + token,
      }
    }

    try {
      let streamSucceeded = false

      try {
        await chatApi.streamMessage(
          content,
          activeSessionId.value,
          (token) => {
            streamingStatus.value = null
            appendToken(token)
          },
          (doneEvent) => {
            streamingStatus.value = null
            streamSucceeded = true
            // Remove optimistic user message
            messages.value = messages.value.filter(
              (m) => !('isOptimistic' in m) || (m as OptimisticMessage).id !== optimisticId,
            )
            // Build a real ChatMessage from the streamed content
            const assistantContent = normalizeAssistantContent(streamingMessage.value?.content ?? '')
            messages.value = [
              ...messages.value,
              {
                id: Date.now(),
                content,
                role: 'user',
                created_at: new Date().toISOString(),
              },
              {
                id: Date.now() + 1,
                content: assistantContent,
                role: 'assistant',
                metadata: {
                  sources: doneEvent.sources,
                  document_contents: doneEvent.document_contents,
                  source_kind: doneEvent.source_kind,
                  disclaimer: doneEvent.disclaimer ?? null,
                  kb_resolved: doneEvent.kb_resolved ?? null,
                  router_decision: doneEvent.router_decision ?? null,
                },
                created_at: new Date().toISOString(),
              },
            ]
            if (doneEvent.session_id) {
              activeSessionId.value = doneEvent.session_id
              upsertSession(doneEvent.session_id, content)
            }
          },
          () => {
            // Streaming error event — fall through to non-streaming fallback below
          },
          (statusMsg) => {
            streamingStatus.value = statusMsg
          },
          researchMode.value,
        )
      } catch {
        // Fetch-level failure (network, CORS, etc.) — fall through to fallback
      }

      if (!streamSucceeded) {
        // Fallback: non-streaming endpoint
        streamingMessage.value = null
        const res = await chatApi.sendMessage(content, activeSessionId.value, researchMode.value)
        messages.value = messages.value.filter(
          (m) => !('isOptimistic' in m) || (m as OptimisticMessage).id !== optimisticId,
        )
        messages.value = [...messages.value, res.user_message, res.assistant_message]
        activeSessionId.value = res.session_id
        upsertSession(res.session_id, content)
      }
    } catch (err) {
      messages.value = messages.value.filter(
        (m) => !('isOptimistic' in m) || (m as OptimisticMessage).id !== optimisticId,
      )
      retryableSendContent.value = content
      throw err
    } finally {
      streamingMessage.value = null
      streamingStatus.value = null
      isSendingMessage.value = false
    }
  }

  function setChatMode(mode: ChatMode): void {
    chatMode.value = mode
    if (mode === 'agent') {
      researchMode.value = 'kb'
    }
  }

  async function retryLastFailedSend(): Promise<void> {
    if (!retryableSendContent.value) return
    const content = retryableSendContent.value
    await sendMessage(content)
  }

  function dismissRetry(): void {
    retryableSendContent.value = null
  }

  function addUserMessage(content: string): void {
    messages.value = [
      ...messages.value,
      {
        id: Date.now() + Math.floor(Math.random() * 1000),
        content,
        role: 'user',
        created_at: new Date().toISOString(),
      } as ChatMessage,
    ]
  }

  /**
   * Record an agent turn into the chat transcript (Option C upsert).
   *
   * One in-memory bubble per ``agent_session_id``. The first turn appends;
   * every subsequent turn updates that same bubble in place so the live
   * view matches the server's upserted ``chat_messages`` row. When the
   * backend stamps ``chat_message_id``, we adopt it as the bubble id so
   * an immediate refresh does not duplicate the row.
   */
  function findAgentBubbleIndex(
    sessionId: string,
    chatMessageId: number | null,
  ): number {
    return messages.value.findIndex((msg) => {
      if (msg.role !== 'assistant') return false
      const chatMsg = msg as ChatMessage
      if (chatMessageId != null && chatMsg.id === chatMessageId) return true
      const meta = chatMsg.metadata
      if (meta?.agent_turn?.session_id === sessionId) return true
      if (meta?.agent_summary?.agent_session_id === sessionId) return true
      return false
    })
  }

  function recordAgentTurnIntoChat(content: string, turn: import('@/types/helpdesk').AgentTurn): void {
    const persistedId =
      typeof turn.chat_message_id === 'number' ? turn.chat_message_id : null
    const idx = findAgentBubbleIndex(turn.session_id, persistedId)

    if (idx >= 0) {
      const existing = messages.value[idx] as ChatMessage
      const next: ChatMessage = {
        ...existing,
        id: persistedId ?? existing.id,
        content,
        metadata: { ...existing.metadata, agent_turn: turn },
      }
      messages.value = [
        ...messages.value.slice(0, idx),
        next,
        ...messages.value.slice(idx + 1),
      ]
      return
    }

    addAssistantMessage(content, { agent_turn: turn }, persistedId)
  }

  function addAssistantMessage(
    content: string,
    metadata?: ChatMessage['metadata'],
    persistedId?: number | null,
  ): void {
    messages.value = [
      ...messages.value,
      {
        id: persistedId ?? Date.now() + Math.floor(Math.random() * 1000),
        content,
        role: 'assistant',
        metadata,
        created_at: new Date().toISOString(),
      } as ChatMessage,
    ]
  }

  const currentMessages = computed<ChatMessage[]>(() =>
    messages.value.filter(
      (m): m is ChatMessage =>
        !('isOptimistic' in m) && !('isStreaming' in m),
    ),
  )

  function startNewChat(): void {
    activeSessionId.value = null
    messages.value = []
    retryableSendContent.value = null
    streamingMessage.value = null
    chatMode.value = 'ask'
  }

  function clear(): void {
    sessions.value = []
    activeSessionId.value = null
    messages.value = []
    isLoading.value = false
    isSendingMessage.value = false
    retryableSendContent.value = null
    streamingMessage.value = null
    chatMode.value = 'ask'
  }

  return {
    sessions,
    activeSessionId,
    messages,
    streamingMessage,
    streamingStatus,
    isLoading,
    isSendingMessage,
    sessionsLoading,
    retryableSendContent,
    researchMode,
    chatMode,
    activeSession,
    addUserMessage,
    addAssistantMessage,
    recordAgentTurnIntoChat,
    currentMessages,
    fetchSessions,
    loadSession,
    deleteSession,
    sendMessage,
    setChatMode,
    retryLastFailedSend,
    dismissRetry,
    startNewChat,
    clear,
  }
})
