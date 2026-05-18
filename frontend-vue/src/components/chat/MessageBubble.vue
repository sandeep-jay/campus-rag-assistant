<script setup lang="ts">
import { ref, computed } from 'vue'
import { Copy, Check } from 'lucide-vue-next'
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
    // clipboard not available in all contexts
  }
}

function formatTime(dateStr: string): string {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <!-- Full-width stacked row; assistant gets subtle tint (ChatGPT-style lane) -->
  <div
    class="w-full px-4 md:px-6 py-4"
    :class="isAssistant(message) ? 'bg-muted/30 dark:bg-muted/40' : ''"
    :data-testid="isAssistant(message) ? 'assistant-bubble' : 'user-bubble'"
  >
    <div class="max-w-4xl mx-auto flex gap-4 items-start">
      <!-- Avatar column: always left (U / AI) -->
      <div
        class="flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold"
        :class="isAssistant(message)
          ? 'bg-primary text-primary-foreground'
          : 'bg-secondary text-secondary-foreground'"
        aria-hidden="true"
      >
        {{ isAssistant(message) ? 'AI' : 'U' }}
      </div>

      <div
        class="flex flex-col gap-2 flex-1 min-w-0 text-sm"
        :class="isOptimistic(message) ? 'opacity-70' : ''"
      >
        <!-- Assistant: sanitized markdown — ONLY place v-html is used -->
        <div
          v-if="isAssistant(message)"
          class="prose prose-sm dark:prose-invert max-w-none leading-relaxed [&_p]:mb-3 [&_h2]:mt-6 [&_h2]:mb-3 [&_h2]:text-base [&_h2]:font-semibold [&_h2]:border-b [&_h2]:border-border [&_h2]:pb-1 [&_ul]:my-3 [&_ul]:list-disc [&_ul]:space-y-2 [&_ul]:pl-6 [&_ol]:my-3 [&_ol]:list-decimal [&_ol]:space-y-2 [&_ol]:pl-6 [&_li]:leading-relaxed [&_strong]:font-semibold [&_pre]:overflow-x-auto [&_code]:text-xs"
          v-html="renderMarkdown(message.content)"
        />
        <!-- Streaming cursor — only visible while SSE is open -->
        <span
          v-if="isStreaming"
          class="inline-block w-2 h-4 ml-0.5 bg-current align-middle animate-pulse motion-reduce:animate-none"
          aria-hidden="true"
        />
        <!-- User: plain text — no markdown rendering, no v-html -->
        <p v-if="!isAssistant(message)" class="whitespace-pre-wrap break-words text-foreground leading-relaxed">
          {{ message.content }}
        </p>

        <span class="text-xs text-muted-foreground">
          {{ formatTime(message.created_at) }}
        </span>

        <!-- Assistant actions: copy + feedback (hidden until persisted message id exists) -->
        <div
          v-if="isAssistant(message) && !isOptimistic(message) && !isStreaming"
          class="flex items-center justify-between gap-2"
        >
          <MessageFeedback :message-id="message.id as number" />

          <button
            aria-label="Copy message to clipboard"
            class="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            @click="copyMessage"
          >
            <Check v-if="isCopied" class="h-4 w-4 text-green-600" aria-hidden="true" />
            <Copy v-else class="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        <template v-if="isAssistant(message) && !isOptimistic(message) && hasSources && !isStreaming">
          <SourcesSummary
            :sources="sources"
            :expanded="showSources"
            :panel-id="panelId"
            :document-contents-count="documentContents.length"
            @toggle="showSources = !showSources"
          />
          <div :id="panelId" v-if="showSources" class="mt-2">
            <SourcesPanel :sources="sources" :document-contents="documentContents" />
          </div>
        </template>
      </div>
    </div>
  </div>
</template>
