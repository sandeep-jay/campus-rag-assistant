<script setup lang="ts">
import { ref } from 'vue'
import { ExternalLink } from 'lucide-vue-next'
import type { Source, DocContent } from '@/api/types'
import { isSafeUrl } from '@/utils/url'

defineProps<{
  sources: Source[]
  documentContents: DocContent[]
}>()

const activeTab = ref<'sources' | 'content'>('sources')
</script>

<template>
  <div class="mt-3 rounded-lg border border-border bg-muted/30" data-testid="sources-panel">
    <div v-if="sources.length === 0 && documentContents.length === 0" class="px-3 py-2">
      <p class="text-xs text-muted-foreground">No sources available for this response.</p>
    </div>

    <template v-else>
      <!-- Tab switcher -->
      <div class="flex border-b border-border" role="tablist">
        <button
          role="tab"
          :aria-selected="activeTab === 'sources'"
          class="px-3 py-1.5 text-xs font-medium transition-colors"
          :class="activeTab === 'sources' ? 'text-foreground border-b-2 border-primary' : 'text-muted-foreground hover:text-foreground'"
          @click="activeTab = 'sources'"
        >
          Sources
        </button>
        <button
          v-if="documentContents.length > 0"
          role="tab"
          :aria-selected="activeTab === 'content'"
          class="px-3 py-1.5 text-xs font-medium transition-colors"
          :class="activeTab === 'content' ? 'text-foreground border-b-2 border-primary' : 'text-muted-foreground hover:text-foreground'"
          @click="activeTab = 'content'"
        >
          Content
        </button>
      </div>

      <!-- Sources tab -->
      <div v-if="activeTab === 'sources'" class="p-2 space-y-2">
        <div
          v-for="(source, idx) in sources"
          :key="idx"
          class="rounded-md border border-border bg-background p-2 text-xs space-y-1"
        >
          <p class="font-medium text-foreground">{{ source.short_description }}</p>
          <div class="flex flex-wrap gap-x-3 gap-y-0.5 text-muted-foreground">
            <span v-if="source.kb_number">KB: {{ source.kb_number }}</span>
            <span v-if="source.kb_category">{{ source.kb_category }}</span>
            <span v-if="source.project">{{ source.project }}</span>
            <span v-if="typeof source.score === 'number'">Score: {{ source.score.toFixed(3) }}</span>
            <span v-else>Score: N/A</span>
          </div>
          <!-- URL only rendered if it passes safety check -->
          <a
            v-if="isSafeUrl(source.kb_url)"
            :href="source.kb_url"
            target="_blank"
            rel="noopener noreferrer"
            class="flex items-center gap-1 text-primary hover:underline truncate"
          >
            <ExternalLink class="h-3 w-3 flex-shrink-0" aria-hidden="true" />
            {{ source.kb_url }}
          </a>
        </div>
      </div>

      <!-- Content tab -->
      <div v-if="activeTab === 'content'" class="p-2 space-y-2">
        <div
          v-for="(doc, idx) in documentContents"
          :key="idx"
          class="rounded-md border border-border bg-background p-2 text-xs space-y-1"
        >
          <p class="font-medium text-foreground">{{ doc.metadata.short_description }}</p>
          <p class="text-muted-foreground whitespace-pre-wrap leading-relaxed">
            {{ doc.content.length > 500 ? doc.content.slice(0, 500) + '…' : doc.content }}
          </p>
        </div>
      </div>
    </template>
  </div>
</template>
