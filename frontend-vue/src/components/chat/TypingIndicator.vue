<script setup lang="ts">
defineProps<{ status?: string | null }>()
</script>

<template>
  <div class="px-4 sm:px-6 lg:px-8 py-3">
    <div class="chat-container flex gap-3 items-center">
      <div class="flex-shrink-0 h-9 w-9" aria-hidden="true" />
      <div role="status" aria-live="polite" aria-atomic="true" class="flex items-center gap-2">
        <div class="flex items-center gap-2 rounded-2xl bg-muted px-4 py-3 border border-border">
          <span class="sr-only">{{ status || 'Assistant is thinking' }}</span>
          <span v-if="status" class="text-chat-caption text-muted-foreground">{{ status }}</span>
          <span v-else class="text-chat-caption text-muted-foreground">Thinking…</span>
          <span aria-hidden="true" class="h-2 w-2 rounded-full bg-muted-foreground animate-bounce motion-reduce:animate-none" style="animation-delay: 0ms" />
          <span aria-hidden="true" class="h-2 w-2 rounded-full bg-muted-foreground animate-bounce motion-reduce:animate-none" style="animation-delay: 150ms" />
          <span aria-hidden="true" class="h-2 w-2 rounded-full bg-muted-foreground animate-bounce motion-reduce:animate-none" style="animation-delay: 300ms" />
        </div>
      </div>
    </div>
  </div>
</template>
