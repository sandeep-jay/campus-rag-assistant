import { ref, nextTick } from 'vue'
import { useChatStore } from '@/stores/chat'
import type { ComponentPublicInstance } from 'vue'

export interface UseChatReturn {
  sendMessage: (content: string) => Promise<void>
  inputRef: ReturnType<typeof ref<ComponentPublicInstance & { focus: () => void } | null>>
}

export function useChat(): UseChatReturn {
  const chatStore = useChatStore()
  const inputRef = ref<(ComponentPublicInstance & { focus: () => void }) | null>(null)

  async function sendMessage(content: string): Promise<void> {
    try {
      await chatStore.sendMessage(content)
    } finally {
      // Always restore focus to input after send attempt (success or failure)
      await nextTick()
      inputRef.value?.focus()
    }
  }

  return { sendMessage, inputRef }
}
