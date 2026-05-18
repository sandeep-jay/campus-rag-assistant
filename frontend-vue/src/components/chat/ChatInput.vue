<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { SendHorizontal } from 'lucide-vue-next'

const props = withDefaults(defineProps<{ disabled?: boolean }>(), { disabled: false })
const emit = defineEmits<{ submit: [content: string] }>()

const content = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)

defineExpose({ focus: () => textareaRef.value?.focus() })

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
</script>

<template>
  <form
    class="border-t border-border bg-background px-4 md:px-6 py-4"
    @submit.prevent="handleSubmit"
  >
    <div class="flex items-end gap-2 max-w-4xl mx-auto">
      <textarea
        ref="textareaRef"
        v-model="content"
        rows="1"
        :disabled="disabled"
        placeholder="Type a message… (Enter to send, Shift+Enter for newline)"
        aria-label="Message input"
        class="flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 max-h-40 overflow-y-auto"
        @keydown="handleKeydown"
        @input="autoResize"
      />
      <button
        type="submit"
        :disabled="disabled || !content.trim()"
        aria-label="Send message"
        class="flex-shrink-0 rounded-md bg-primary p-2 text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
      >
        <SendHorizontal class="h-5 w-5" aria-hidden="true" />
      </button>
    </div>
    <p class="text-xs text-muted-foreground text-center mt-2">
      AI responses may be inaccurate. Always verify important information.
    </p>
  </form>
</template>
