<script setup lang="ts">
import { storeToRefs } from "pinia"
import { useRouter } from "vue-router"
import { PlusCircle } from "lucide-vue-next"
import { useChatStore } from "@/stores/chat"
import SessionList from "./SessionList.vue"

defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: [] }>()

const router = useRouter()
const chatStore = useChatStore()
const { sessions, activeSessionId, sessionsLoading } = storeToRefs(chatStore)

async function selectSession(id: number): Promise<void> {
  emit("close")
  await router.push(`/chat/${id}`)
}

async function deleteSession(id: number): Promise<void> {
  await chatStore.deleteSession(id)
  if (chatStore.activeSessionId === null) {
    await router.push("/chat")
  }
}

function startNewChat(): void {
  chatStore.startNewChat()
  emit("close")
  router.push("/chat")
}
</script>

<template>
  <aside
    aria-label="Chat history"
    class="flex flex-col w-72 flex-shrink-0 border-r border-border bg-background h-full
      fixed inset-y-0 left-0 z-50 shadow-xl
      transition-transform duration-200 ease-out motion-reduce:transition-none
      md:relative md:z-auto md:shadow-none md:translate-x-0"
    :class="open ? 'translate-x-0' : '-translate-x-full md:translate-x-0'"
  >
    <div class="flex items-center justify-between px-4 h-14 border-b border-border flex-shrink-0">
      <span class="font-medium text-sm text-foreground">Conversations</span>
      <button
        aria-label="Start new conversation"
        class="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
        @click="startNewChat"
      >
        <PlusCircle class="h-5 w-5" aria-hidden="true" />
      </button>
    </div>

    <div v-if="sessionsLoading" class="flex-1 p-2 space-y-2" aria-busy="true" aria-label="Loading sessions">
      <div v-for="i in 5" :key="i" class="h-9 rounded-lg bg-muted animate-pulse motion-reduce:animate-none" />
    </div>

    <SessionList
      v-else
      :sessions="sessions"
      :active-session-id="activeSessionId"
      @select="selectSession"
      @delete="deleteSession"
    />
  </aside>
</template>
