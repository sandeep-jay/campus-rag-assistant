<script setup lang="ts">
import { computed } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
import type { Source } from '@/api/types'
import { isSafeUrl } from '@/utils/url'

const props = withDefaults(
  defineProps<{
    sources: Source[]
    expanded: boolean
    panelId: string
    maxChips?: number
    /** When sources is empty but document chunks exist, show a content-only toggle label */
    documentContentsCount?: number
  }>(),
  { maxChips: 3, documentContentsCount: 0 },
)

const emit = defineEmits<{ toggle: [] }>()

const totalLabelCount = computed(() => {
  if (props.sources.length > 0) return props.sources.length
  return props.documentContentsCount
})

const toggleLabel = computed(() => {
  if (props.sources.length > 0) return `Sources (${totalLabelCount.value})`
  return `Content (${totalLabelCount.value})`
})

const visibleChips = computed(() => props.sources.slice(0, props.maxChips))
const overflowCount = computed(() => Math.max(0, props.sources.length - props.maxChips))

function chipLabel(source: Source): string {
  return source.kb_number?.trim() || 'Source'
}
</script>

<template>
  <div
    v-if="sources.length > 0 || documentContentsCount > 0"
    class="flex w-full flex-col items-start gap-2 pt-1 sm:flex-row sm:flex-wrap sm:items-center"
    data-testid="sources-summary"
  >
    <button
      type="button"
      class="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-2.5 py-1 text-xs font-medium text-foreground hover:bg-accent transition-colors"
      :aria-expanded="expanded"
      :aria-controls="panelId"
      :aria-label="`${toggleLabel}, ${expanded ? 'expanded' : 'collapsed'}`"
      @click="emit('toggle')"
    >
      <span>{{ toggleLabel }}</span>
      <ChevronDown
        class="h-3.5 w-3.5 text-muted-foreground transition-transform shrink-0"
        :class="expanded ? 'rotate-180' : ''"
        aria-hidden="true"
      />
    </button>

    <template v-if="sources.length > 0">
      <template v-for="(source, idx) in visibleChips" :key="idx">
        <a
          v-if="isSafeUrl(source.kb_url)"
          :href="source.kb_url"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex max-w-[10rem] truncate rounded-full border border-border bg-muted/50 px-2 py-0.5 text-xs font-medium text-foreground hover:bg-accent"
          :title="source.short_description"
        >
          {{ chipLabel(source) }}
        </a>
        <span
          v-else
          class="inline-flex max-w-[10rem] truncate rounded-full border border-border bg-muted/30 px-2 py-0.5 text-xs text-muted-foreground"
          :title="source.short_description"
        >
          {{ chipLabel(source) }}
        </span>
      </template>

      <button
        v-if="overflowCount > 0"
        type="button"
        class="inline-flex rounded-full border border-dashed border-border px-2 py-0.5 text-xs text-muted-foreground hover:bg-accent hover:text-foreground"
        @click="emit('toggle')"
      >
        +{{ overflowCount }} more
      </button>
    </template>
  </div>
</template>
