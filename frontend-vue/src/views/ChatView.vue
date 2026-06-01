<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { toast } from 'vue-sonner'
import { useChatStore } from '@/stores/chat'
import { useHelpdeskStore } from '@/stores/helpdesk'
import type { AgentTurn } from '@/types/helpdesk'
import { trackHelpdeskAgentEvent } from '@/utils/telemetry'
import MessageList from '@/components/chat/MessageList.vue'
import ChatInput from '@/components/chat/ChatInput.vue'
import TypingIndicator from '@/components/chat/TypingIndicator.vue'

const route = useRoute()
const router = useRouter()
const chatStore = useChatStore()
const helpdeskStore = useHelpdeskStore()
const { messages, streamingMessage, streamingStatus, isSendingMessage, isLoading, activeSessionId, retryableSendContent, researchMode, chatMode } =
  storeToRefs(chatStore)
const { agentRunning, agentStatus, agentSteps, activeTurn } = storeToRefs(helpdeskStore)

const chatInputRef = ref<InstanceType<typeof ChatInput> | null>(null)
const messageListRef = ref<HTMLElement | null>(null)

async function scrollToBottom(): Promise<void> {
  await nextTick()
  const el = messageListRef.value
  if (el) el.scrollTop = el.scrollHeight
}

watch(
  () => route.params.sessionId,
  async (id) => {
    if (id && typeof id === 'string') {
      try {
        await chatStore.loadSession(Number(id))
      } catch {
        toast.error('Failed to load conversation.')
        router.push('/chat')
      }
    } else {
      chatStore.startNewChat()
      helpdeskStore.clearAgentTurn()
    }
    await scrollToBottom()
  },
  { immediate: true },
)

onMounted(async () => {
  await chatStore.fetchSessions()
})

watch(messages, scrollToBottom, { deep: true })
watch(streamingMessage, scrollToBottom, { deep: true })

function pendingQuestionId(turn: AgentTurn | null): string | undefined {
  return turn?.debug_trace?.at(-1)?.message ?? undefined
}

function appendAgentTurn(turn: AgentTurn): void {
  helpdeskStore.recordAgentTurn(turn)
  chatStore.addAssistantMessage(turn.message, { agent_turn: turn })
  if (turn.draft) {
    helpdeskStore.openModal()
  }
}

async function sendAgentMessage(content: string): Promise<void> {
  chatStore.addUserMessage(content)
  const turn = activeTurn.value
  const next = turn
    ? await helpdeskStore.resumeAgent({
        session_id: turn.session_id,
        reply: content,
        pending_question_id: pendingQuestionId(turn),
        chat_session_id: chatStore.activeSessionId,
      })
    : await helpdeskStore.startAgent(
        chatStore.currentMessages.map((m) => ({ role: m.role, content: m.content })),
        chatStore.activeSessionId,
      )
  if (next) appendAgentTurn(next)
}

async function handleSend(content: string): Promise<void> {
  try {
    if (chatMode.value === 'agent') {
      await sendAgentMessage(content)
    } else {
      await chatStore.sendMessage(content)
      if (activeSessionId.value && !route.params.sessionId) {
        await router.replace(`/chat/${activeSessionId.value}`)
      }
    }
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Failed to send message. Please try again.')
  } finally {
    await scrollToBottom()
    chatInputRef.value?.focus()
  }
}

async function setMode(mode: 'ask' | 'agent'): Promise<void> {
  if (mode === chatMode.value) return
  if (mode === 'ask' && activeTurn.value) {
    const confirmed = window.confirm('Leave helpdesk agent mode? This cancels the current helpdesk workflow without filing a ticket.')
    if (!confirmed) return
    const aborted = await helpdeskStore.abortAgent(activeTurn.value.session_id, chatStore.activeSessionId)
    if (aborted) {
      chatStore.recordAgentTurnIntoChat(aborted.message, aborted)
    } else {
      return
    }
  }
  chatStore.setChatMode(mode)
  trackHelpdeskAgentEvent('mode_changed', { mode })
}

async function handleRetrySend(): Promise<void> {
  try {
    await chatStore.retryLastFailedSend()
    if (activeSessionId.value && !route.params.sessionId) {
      await router.replace(`/chat/${activeSessionId.value}`)
    }
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Retry failed. Please try again.')
  } finally {
    await scrollToBottom()
    chatInputRef.value?.focus()
  }
}

function handlePromptSelected(prompt: string): void {
  handleSend(prompt)
}
</script>

<template>
  <main
    id="main-content"
    :aria-busy="isLoading || isSendingMessage || agentRunning"
    class="flex flex-col flex-1 min-h-0 overflow-hidden bg-background"
  >
    <div class="flex-shrink-0 border-b border-border bg-background/95 px-4 py-2">
      <div class="chat-container flex items-center justify-between gap-3">
        <div>
          <p class="text-chat-label text-foreground">Chat mode</p>
          <p class="text-chat-caption text-muted-foreground">
            {{ chatMode === 'agent' ? 'Helpdesk workflow: replies continue the agent session.' : 'Ask mode: replies go to the knowledge assistant.' }}
          </p>
        </div>
        <button
          type="button"
          role="switch"
          aria-label="Toggle helpdesk agent mode"
          :aria-checked="chatMode === 'agent'"
          class="inline-flex items-center rounded-full border border-border bg-card p-1 text-chat-ui shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          @click="setMode(chatMode === 'agent' ? 'ask' : 'agent')"
        >
          <span
            class="rounded-full px-3 py-1 transition-colors"
            :class="chatMode === 'ask' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground'"
          >
            Ask
          </span>
          <span
            class="rounded-full px-3 py-1 transition-colors"
            :class="chatMode === 'agent' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground'"
          >
            Agent
          </span>
        </button>
      </div>
    </div>

    <div
      ref="messageListRef"
      class="flex-1 min-h-0 overflow-y-auto scroll-smooth"
      tabindex="-1"
    >
      <MessageList
        :messages="messages"
        :streaming-message="streamingMessage"
        @prompt-selected="handlePromptSelected"
      />
      <TypingIndicator
        v-if="(isSendingMessage && !streamingMessage?.content) || agentRunning"
        :status="agentRunning ? agentStatus : streamingStatus"
        :agent-steps="agentRunning ? agentSteps : []"
      />
    </div>

    <div
      v-if="retryableSendContent"
      class="flex-shrink-0 border-t border-border bg-muted/30 px-4 py-2 text-chat-ui flex items-center justify-between gap-3"
      role="status"
      aria-live="polite"
    >
      <span>Last message failed to send.</span>
      <div class="flex items-center gap-2">
        <button type="button" class="underline underline-offset-2" @click="handleRetrySend">Retry</button>
        <button type="button" class="text-muted-foreground" @click="chatStore.dismissRetry">Dismiss</button>
      </div>
    </div>

    <div class="flex-shrink-0 border-t border-border bg-card/95 backdrop-blur-sm shadow-pop">
      <ChatInput
        ref="chatInputRef"
        v-model:research-mode="researchMode"
        :chat-mode="chatMode"
        :disabled="isSendingMessage || agentRunning"
        @submit="handleSend"
      />
    </div>
  </main>
</template>
