<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { Check } from 'lucide-vue-next'

const props = withDefaults(
  defineProps<{
    modelValue: string | null
    choices: string[]
    name?: string
    disabled?: boolean
  }>(),
  { modelValue: null, disabled: false },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: string): void
  (event: 'submit', value: string): void
}>()

const radios = ref<HTMLButtonElement[]>([])

function select(choice: string): void {
  if (props.disabled) return
  emit('update:modelValue', choice)
}

async function focusIndex(index: number): Promise<void> {
  await nextTick()
  const target = radios.value[index]
  if (target && typeof target.focus === 'function') target.focus()
}

function onKey(event: KeyboardEvent, currentIndex: number): void {
  if (props.disabled) return
  const last = props.choices.length - 1
  let nextIndex = currentIndex
  switch (event.key) {
    case 'ArrowDown':
    case 'ArrowRight':
      nextIndex = currentIndex >= last ? 0 : currentIndex + 1
      break
    case 'ArrowUp':
    case 'ArrowLeft':
      nextIndex = currentIndex <= 0 ? last : currentIndex - 1
      break
    case 'Home':
      nextIndex = 0
      break
    case 'End':
      nextIndex = last
      break
    case ' ':
    case 'Enter':
      event.preventDefault()
      select(props.choices[currentIndex])
      if (event.key === 'Enter') emit('submit', props.choices[currentIndex])
      return
    default:
      return
  }
  event.preventDefault()
  select(props.choices[nextIndex])
  void focusIndex(nextIndex)
}
</script>

<template>
  <div
    role="radiogroup"
    class="flex flex-col gap-1.5"
    data-testid="radio-list"
  >
    <button
      v-for="(choice, index) in choices"
      :key="choice"
      ref="radios"
      type="button"
      role="radio"
      :aria-checked="modelValue === choice"
      :tabindex="modelValue === choice || (modelValue === null && index === 0) ? 0 : -1"
      :disabled="disabled"
      :data-selected="modelValue === choice ? 'true' : 'false'"
      class="group flex w-full items-center gap-2 rounded-md border border-border bg-card px-3 py-2 text-left text-chat-ui transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 disabled:cursor-not-allowed data-[selected=true]:border-primary data-[selected=true]:bg-primary/5 data-[selected=true]:text-foreground"
      @click="select(choice)"
      @keydown="onKey($event, index)"
    >
      <span
        aria-hidden="true"
        class="flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-border bg-background group-data-[selected=true]:border-primary group-data-[selected=true]:bg-primary group-data-[selected=true]:text-primary-foreground"
      >
        <Check v-if="modelValue === choice" class="h-3 w-3" />
      </span>
      <span class="flex-1 truncate">{{ choice }}</span>
    </button>
  </div>
</template>
