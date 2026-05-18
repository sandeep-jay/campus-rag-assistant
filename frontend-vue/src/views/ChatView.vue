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
const { messages, streamingMessage, isSendingMessage, isLoading, activeSessionId, retryableSendContent } =
  storeToRefs(chatStore)

const chatInputRef = ref<InstanceType<typeof ChatInput> | null>(null)
const messageListRef = ref<HTMLElement | null>(null)

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
  },
  { immediate: true },
)

onMounted(async () => {
  await chatStore.fetchSessions()
})

watch(messages, async () => {
  await nextTick()
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }
})

async function handleSend(content: string): Promise<void> {
  try {
    await chatStore.sendMessage(content)
    if (activeSessionId.value && !route.params.sessionId) {
      await router.replace(`/chat/${activeSessionId.value}`)
    }
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Failed to send message. Please try again.')
  } finally {
    await nextTick()
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
    await nextTick()
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
    class="flex flex-col flex-1 overflow-hidden"
  >
    <div ref="messageListRef" class="flex-1 overflow-y-auto">
      <MessageList
        :messages="messages"
        :streaming-message="streamingMessage"
        @prompt-selected="handlePromptSelected"
      />
      <!-- TypingIndicator shown only when no streaming content yet (initial wait) -->
      <TypingIndicator v-if="isSendingMessage && !streamingMessage?.content" />
    </div>

    <div
      v-if="retryableSendContent"
      class="border-t border-border bg-muted/30 px-4 py-2 text-sm flex items-center justify-between gap-3"
      role="status"
      aria-live="polite"
    >
      <span>Last message failed to send.</span>
      <div class="flex items-center gap-2">
        <button class="underline underline-offset-2" @click="handleRetrySend">Retry</button>
        <button class="text-muted-foreground" @click="chatStore.dismissRetry">Dismiss</button>
      </div>
    </div>

    <ChatInput
      ref="chatInputRef"
      :disabled="isSendingMessage"
      @submit="handleSend"
    />
  </main>
</template>
