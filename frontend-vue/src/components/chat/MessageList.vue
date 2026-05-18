<script setup lang="ts">
import type { DisplayMessage, StreamingMessage } from '@/api/types'
import MessageBubble from './MessageBubble.vue'

defineProps<{
  messages: DisplayMessage[]
  streamingMessage?: StreamingMessage | null
}>()

defineEmits<{
  'prompt-selected': [prompt: string]
}>()
</script>

<template>
  <div
    role="log"
    aria-label="Conversation"
    aria-live="polite"
    aria-relevant="additions"
    class="overflow-y-auto flex-1"
  >
    <ul role="list" class="flex flex-col gap-0 py-4 min-h-full">
      <li v-if="messages.length === 0 && !streamingMessage" class="flex items-center justify-center flex-1 py-16">
        <div class="text-center space-y-4 max-w-md mx-auto px-4">
          <div class="text-4xl">💬</div>
          <h2 class="text-xl font-semibold text-foreground">Start a new conversation</h2>
          <p class="text-muted-foreground text-sm">
            Ask me anything about BCourses. I'll search through the knowledge base to find the best answer for you.
          </p>
          <div class="grid grid-cols-1 gap-2 mt-4 text-left">
            <p class="text-xs font-medium text-muted-foreground uppercase tracking-wide">Try asking:</p>
            <button
              v-for="prompt in samplePrompts"
              :key="prompt"
              class="text-sm text-left p-3 rounded-lg border border-border hover:bg-accent hover:text-accent-foreground transition-colors"
              @click="$emit('prompt-selected', prompt)"
            >
              {{ prompt }}
            </button>
          </div>
        </div>
      </li>

      <li
        v-for="message in messages"
        :key="'id' in message ? message.id : (message as any).id"
        class="list-none w-full"
      >
        <MessageBubble :message="message" />
      </li>

      <!-- Live streaming assistant message -->
      <li v-if="streamingMessage" class="list-none w-full" aria-live="polite" aria-atomic="false">
        <MessageBubble :message="streamingMessage" :is-streaming="true" />
      </li>
    </ul>
  </div>
</template>

<script lang="ts">
const samplePrompts = [
  'How do I submit an assignment in BCourses?',
  'How do I check my grades?',
  'How do I join a course discussion?',
  'How do I download course files?',
]
</script>
