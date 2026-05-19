<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { toast } from 'vue-sonner'
import { useChatStore } from '@/stores/chat'
import MessageList from '@/components/chat/MessageList.vue'
import ChatInput from '@/components/chat/ChatInput.vue'
import TypingIndicator from '@/components/chat/TypingIndicator.vue'

const route = useRoute()
const router = useRouter()
const chatStore = useChatStore()
const { messages, streamingMessage, streamingStatus, isSendingMessage, isLoading, activeSessionId, retryableSendContent } =
  storeToRefs(chatStore)

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

async function handleSend(content: string): Promise<void> {
  try {
    await chatStore.sendMessage(content)
    if (activeSessionId.value && !route.params.sessionId) {
      await router.replace(`/chat/${activeSessionId.value}`)
    }
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Failed to send message. Please try again.')
  } finally {
    await scrollToBottom()
    chatInputRef.value?.focus()
  }
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
    :aria-busy="isLoading || isSendingMessage"
    class="flex flex-col flex-1 min-h-0 overflow-hidden bg-background"
  >
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
        v-if="isSendingMessage && !streamingMessage?.content"
        :status="streamingStatus"
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

    <div class="flex-shrink-0 border-t border-border bg-background/95 backdrop-blur-sm shadow-[0_-4px_24px_-8px_rgba(0,0,0,0.12)] dark:shadow-[0_-4px_24px_-8px_rgba(0,0,0,0.45)]">
      <ChatInput ref="chatInputRef" :disabled="isSendingMessage" @submit="handleSend" />
    </div>
  </main>
</template>
