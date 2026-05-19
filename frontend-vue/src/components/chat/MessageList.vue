<script setup lang="ts">
import { MessageCircle, Sparkles } from 'lucide-vue-next'
import type { DisplayMessage, StreamingMessage } from '@/api/types'
import MessageBubble from './MessageBubble.vue'

defineProps<{
  messages: DisplayMessage[]
  streamingMessage?: StreamingMessage | null
}>()

defineEmits<{
  'prompt-selected': [prompt: string]
}>()

const samplePrompts = ['How do I submit an assignment in the learning platform?', 'How do I check my grades?', 'How do I join a course discussion?', 'How do I download course files?']
</script>

<template>
  <div
    role="log"
    aria-label="Conversation"
    aria-live="polite"
    aria-relevant="additions"
    class="py-4 min-h-full"
  >
    <ul role="list" class="flex flex-col">
      <li
        v-if="messages.length === 0 && !streamingMessage"
        class="flex items-center justify-center flex-1 py-12 sm:py-16 list-none"
      >
        <div class="text-center space-y-5 max-w-lg mx-auto px-4">
          <div class="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary mx-auto">
            <MessageCircle class="h-7 w-7" aria-hidden="true" />
          </div>
          <div>
            <h2 class="text-chat-display text-foreground">Campus knowledge assistant</h2>
            <p class="text-muted-foreground text-chat-body mt-2">
              Ask about courses, assignments, grades, and campus resources. Answers are grounded in your knowledge base—not general web search.
            </p>
          </div>
          <div class="rounded-lg border border-border bg-muted/30 px-3 py-2 text-chat-caption text-muted-foreground text-left">
            <Sparkles class="inline h-3.5 w-3.5 mr-1 -mt-0.5 text-primary" aria-hidden="true" />
            Off-topic questions may be declined based on your organization's scope.
          </div>
          <div class="grid grid-cols-1 gap-2 text-left">
            <p class="text-chat-label text-muted-foreground">Try asking</p>
            <button
              v-for="prompt in samplePrompts"
              :key="prompt"
              type="button"
              class="text-chat-ui text-left p-3 rounded-lg border border-border hover:bg-accent hover:text-accent-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              @click="$emit('prompt-selected', prompt)"
            >
              {{ prompt }}
            </button>
          </div>
        </div>
      </li>

      <li
        v-for="message in messages"
        :key="'id' in message ? message.id : (message as { id: string }).id"
        class="list-none w-full"
      >
        <MessageBubble :message="message" />
      </li>

      <li v-if="streamingMessage" class="list-none w-full">
        <MessageBubble :message="streamingMessage" :is-streaming="true" />
      </li>
    </ul>
  </div>
</template>
