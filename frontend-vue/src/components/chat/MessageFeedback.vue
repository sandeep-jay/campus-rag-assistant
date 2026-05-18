<script setup lang="ts">
import { ref } from 'vue'
import { ThumbsUp, ThumbsDown } from 'lucide-vue-next'
import * as chatApi from '@/api/chat'

const props = defineProps<{ messageId: number }>()

const submitted = ref(false)
const selected = ref<'thumbs_up' | 'thumbs_down' | null>(null)

async function submitFeedback(type: 'thumbs_up' | 'thumbs_down'): Promise<void> {
  if (submitted.value) return
  selected.value = type
  submitted.value = true
  try {
    await chatApi.submitFeedback({ message_id: props.messageId, feedback_type: type })
  } catch {
    // silently fail — feedback is non-critical
    submitted.value = false
    selected.value = null
  }
}
</script>

<template>
  <div class="flex items-center gap-1 mt-2">
    <button
      :disabled="submitted"
      :aria-pressed="selected === 'thumbs_up'"
      aria-label="Mark as helpful"
      class="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent disabled:cursor-default disabled:opacity-50 transition-colors"
      :class="{ 'text-green-600': selected === 'thumbs_up' }"
      @click="submitFeedback('thumbs_up')"
    >
      <ThumbsUp class="h-4 w-4" aria-hidden="true" />
    </button>

    <button
      :disabled="submitted"
      :aria-pressed="selected === 'thumbs_down'"
      aria-label="Mark as not helpful"
      class="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent disabled:cursor-default disabled:opacity-50 transition-colors"
      :class="{ 'text-red-600': selected === 'thumbs_down' }"
      @click="submitFeedback('thumbs_down')"
    >
      <ThumbsDown class="h-4 w-4" aria-hidden="true" />
    </button>

    <span v-if="submitted" class="text-xs text-muted-foreground ml-1">
      Thanks for your feedback!
    </span>
  </div>
</template>
