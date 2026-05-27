<script setup lang="ts">
import { ref, computed } from 'vue'
import { Copy, Check, Info } from 'lucide-vue-next'
import type { DisplayMessage, ChatMessage } from '@/api/types'
import { renderMarkdown } from '@/utils/markdown'
import MessageFeedback from './MessageFeedback.vue'
import SourcesPanel from './SourcesPanel.vue'
import SourcesSummary from './SourcesSummary.vue'

const props = defineProps<{ message: DisplayMessage; isStreaming?: boolean }>()

const isCopied = ref(false)
const showSources = ref(false)

function isAssistant(msg: DisplayMessage): boolean {
  return msg.role === 'assistant'
}

function isOptimistic(msg: DisplayMessage): boolean {
  return 'isOptimistic' in msg
}

function getSources(msg: DisplayMessage): ChatMessage['metadata'] {
  if ('metadata' in msg) return msg.metadata
  return undefined
}

const sources = computed(() => getSources(props.message)?.sources ?? [])
const documentContents = computed(() => getSources(props.message)?.document_contents ?? [])
const hasSources = computed(
  () => sources.value.length > 0 || documentContents.value.length > 0,
)

const disclaimer = computed(() => getSources(props.message)?.disclaimer ?? null)

const panelId = computed(() => {
  const id = 'id' in props.message ? String((props.message as { id: number | string }).id) : 'opt'
  return `sources-panel-${id}`
})

async function copyMessage(): Promise<void> {
  try {
    await navigator.clipboard.writeText(props.message.content)
    isCopied.value = true
    setTimeout(() => { isCopied.value = false }, 2000)
  } catch {
    // clipboard not available
  }
}

function formatTime(dateStr: string): string {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <article
    class="w-full py-3 px-4 sm:px-6 lg:px-8"
    :class="isAssistant(message) ? '' : ''"
    :data-testid="isAssistant(message) ? 'assistant-bubble' : 'user-bubble'"
  >
    <!-- Assistant: avatar left, content right -->
    <div v-if="isAssistant(message)" class="chat-container flex gap-3 items-start">
      <div
        class="flex-shrink-0 h-9 w-9 rounded-full flex items-center justify-center text-chat-avatar font-bold uppercase bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-100"
        aria-hidden="true"
      >
        AI
      </div>

      <div class="group/bubble flex min-w-0 flex-1 flex-col gap-1.5 items-start max-w-[95%]">
        <span class="text-chat-label text-muted-foreground px-1">Assistant</span>

        <div
          v-if="isStreaming"
          class="w-full rounded-lg border border-border bg-card px-5 py-4 shadow-soft"
          aria-live="polite"
          aria-atomic="false"
        >
          <p
            v-if="message.content"
            class="whitespace-pre-wrap break-words text-chat-body text-foreground"
          >
            {{ message.content }}
          </p>
          <p v-else class="text-chat-caption text-muted-foreground">Preparing answer…</p>
          <span
            class="inline-block w-0.5 h-4 ml-0.5 bg-primary align-middle animate-pulse motion-reduce:animate-none"
            aria-hidden="true"
          />
        </div>

        <div v-else class="w-full rounded-lg border border-border bg-card px-5 py-4 shadow-soft">
          <div class="chat-prose dark:prose-invert max-w-none text-foreground" v-html="renderMarkdown(message.content)" />
        </div>

        <p
          v-if="disclaimer && !isStreaming"
          class="flex w-full items-start gap-2 rounded-md border border-border bg-muted px-3 py-2 text-chat-caption text-muted-foreground"
          role="note"
          data-testid="web-disclaimer"
        >
          <Info class="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent-subtle-foreground" aria-hidden="true" />
          <span>{{ disclaimer }}</span>
        </p>

        <span class="text-chat-meta text-muted-foreground px-1">
          {{ formatTime(message.created_at) }}
        </span>

        <div
          v-if="!isOptimistic(message) && !isStreaming"
          class="flex w-full flex-col gap-2"
        >
          <!-- Always visible message actions: feedback + copy live in the
               same row so users get the same affordances they expect from
               other chat tools (ChatGPT / Claude). No hover-to-reveal so
               the copy action is discoverable on touch + screen readers. -->
          <div class="flex w-full items-center gap-1">
            <MessageFeedback :message-id="message.id as number" />
            <button
              type="button"
              :aria-label="isCopied ? 'Copied to clipboard' : 'Copy message to clipboard'"
              class="inline-flex items-center gap-1 rounded-md p-1.5 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
              @click="copyMessage"
            >
              <Check v-if="isCopied" class="h-4 w-4 text-green-600" aria-hidden="true" />
              <Copy v-else class="h-4 w-4" aria-hidden="true" />
              <span v-if="isCopied" class="text-xs text-green-700 dark:text-green-400">Copied</span>
            </button>
          </div>

          <template v-if="hasSources">
            <SourcesSummary
              :sources="sources"
              :expanded="showSources"
              :panel-id="panelId"
              :document-contents-count="documentContents.length"
              @toggle="showSources = !showSources"
            />
            <div v-if="showSources" :id="panelId" class="w-full">
              <SourcesPanel :sources="sources" :document-contents="documentContents" />
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- User: content + avatar grouped on the right -->
    <div v-else class="chat-container flex justify-end">
      <div class="flex max-w-[min(85%,40rem)] gap-3 items-end">
        <div class="group/bubble flex min-w-0 flex-col gap-1.5 items-end">
          <span class="text-chat-label user-message-label px-1">You</span>

          <div
            class="user-message-bubble rounded-lg px-4 py-3 shadow-soft"
            :class="isOptimistic(message) ? 'opacity-70' : ''"
          >
            <p class="whitespace-pre-wrap break-words text-chat-body">
              {{ message.content }}
            </p>
          </div>

          <span class="text-chat-meta text-muted-foreground px-1">
            {{ formatTime(message.created_at) }}
          </span>
        </div>

        <div
          class="flex-shrink-0 h-9 w-9 rounded-full flex items-center justify-center text-chat-avatar font-bold uppercase user-message-avatar"
          aria-hidden="true"
        >
          Y
        </div>
      </div>
    </div>
  </article>
</template>
