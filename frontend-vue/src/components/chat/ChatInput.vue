<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { Globe, SendHorizontal } from 'lucide-vue-next'
import type { ResearchMode } from '@/api/types'

const props = withDefaults(
  defineProps<{ disabled?: boolean; researchMode?: ResearchMode }>(),
  { disabled: false, researchMode: 'kb' },
)
const emit = defineEmits<{
  submit: [content: string]
  'update:researchMode': [mode: ResearchMode]
}>()

const content = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)

defineExpose({ focus: () => textareaRef.value?.focus() })

const webEnabled = import.meta.env.VITE_WEB_RESEARCH_ENABLED === 'true'

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSubmit()
  }
}

function handleSubmit(): void {
  const trimmed = content.value.trim()
  if (!trimmed || props.disabled) return
  emit('submit', trimmed)
  content.value = ''
  nextTick(() => textareaRef.value?.focus())
}

function autoResize(event: Event): void {
  const el = event.target as HTMLTextAreaElement
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 160)}px`
}

function toggleWeb(): void {
  emit('update:researchMode', props.researchMode === 'web' ? 'kb' : 'web')
}
</script>

<template>
  <form class="px-4 md:px-6 py-4" @submit.prevent="handleSubmit">
    <div class="chat-container flex flex-col gap-2">
      <div class="flex items-end gap-2">
        <textarea
          ref="textareaRef"
          v-model="content"
          rows="1"
          :disabled="disabled"
          placeholder="Ask about courses, assignments, or campus resources…"
          aria-label="Message input"
          class="flex-1 resize-none rounded-xl border border-input bg-background px-4 py-3 text-chat-ui shadow-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 max-h-40 overflow-y-auto"
          @keydown="handleKeydown"
          @input="autoResize"
        />
        <button
          type="submit"
          :disabled="disabled || !content.trim()"
          aria-label="Send message"
          class="flex-shrink-0 rounded-xl bg-primary p-3 text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-colors shadow-sm"
        >
          <SendHorizontal class="h-5 w-5" aria-hidden="true" />
        </button>
      </div>
      <div class="flex items-center justify-between gap-2 px-1">
        <button
          v-if="webEnabled"
          type="button"
          :aria-pressed="researchMode === 'web'"
          class="inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-chat-caption transition-colors"
          :class="researchMode === 'web'
            ? 'border-primary bg-primary/10 text-primary'
            : 'border-border text-muted-foreground hover:bg-accent'"
          @click="toggleWeb"
        >
          <Globe class="h-3.5 w-3.5" aria-hidden="true" />
          Search the web
        </button>
        <span v-else class="text-chat-caption text-muted-foreground">Knowledge base only</span>
        <span class="text-chat-caption text-muted-foreground">
          {{ researchMode === 'web' ? 'Public web search only (not your knowledge base)' : 'Answers from your knowledge base' }}
        </span>
      </div>
    </div>
  </form>
</template>
