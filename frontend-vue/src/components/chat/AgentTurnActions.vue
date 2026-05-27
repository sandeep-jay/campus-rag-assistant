<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useHelpdeskStore } from '@/stores/helpdesk'
import type { AgentTurn } from '@/types/helpdesk'
import RadioList from './RadioList.vue'

const props = defineProps<{ turn: AgentTurn }>()

const chat = useChatStore()
const helpdesk = useHelpdeskStore()

const pendingQuestionId = computed(() => props.turn.debug_trace?.at(-1)?.message ?? undefined)
const disabled = computed(() => helpdesk.agentRunning)
const inputMode = computed(() => props.turn.input ?? 'pills')

const selected = ref<string | null>(null)

watch(
  () => props.turn.session_id,
  () => { selected.value = null },
  { immediate: true },
)

function appendAgentTurn(turn: AgentTurn): void {
  helpdesk.recordAgentTurn(turn)
  chat.recordAgentTurnIntoChat(turn.message, turn)
  if (turn.draft) {
    helpdesk.openModal()
  }
}

async function submitChoice(choice: string): Promise<void> {
  if (disabled.value) return
  chat.addUserMessage(choice)
  const next = await helpdesk.resumeAgent({
    session_id: props.turn.session_id,
    choice,
    pending_question_id: pendingQuestionId.value,
    chat_session_id: chat.activeSessionId,
  })
  if (next) appendAgentTurn(next)
}

async function onPillClick(choice: string): Promise<void> {
  await submitChoice(choice)
}

async function onRadioSubmit(): Promise<void> {
  if (!selected.value) return
  await submitChoice(selected.value)
}
</script>

<template>
  <template v-if="turn.choices?.length">
    <!-- Pills: terminal one-tap actions (solution feedback). Auto-submit on click. -->
    <div
      v-if="inputMode === 'pills'"
      class="w-full mt-3 flex flex-wrap gap-2"
      data-testid="agent-turn-actions"
      role="group"
      aria-label="Helpdesk agent choices"
    >
      <button
        v-for="choice in turn.choices"
        :key="choice"
        type="button"
        class="inline-flex items-center rounded-md border border-border bg-card px-3 py-1.5 text-chat-ui hover:bg-accent hover:text-accent-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 disabled:cursor-not-allowed"
        :disabled="disabled"
        @click="onPillClick(choice)"
      >
        {{ choice }}
      </button>
    </div>

    <!-- Radio: deliberate single-select with explicit Submit. Renders inline
         within the parent bubble; the bubble's message text is the prompt. -->
    <div
      v-else-if="inputMode === 'radio'"
      class="w-full mt-3"
      data-testid="agent-turn-actions"
      role="group"
      :aria-label="turn.message"
    >
      <RadioList
        v-model="selected"
        :choices="turn.choices"
        :disabled="disabled"
        @submit="onRadioSubmit"
      />
      <div class="mt-3 flex justify-end">
        <button
          type="button"
          class="inline-flex items-center rounded-md bg-primary px-4 py-1.5 text-primary-foreground text-chat-ui hover:bg-primary/90 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 disabled:cursor-not-allowed"
          :disabled="disabled || !selected"
          @click="onRadioSubmit"
        >
          Submit
        </button>
      </div>
    </div>
  </template>
</template>
