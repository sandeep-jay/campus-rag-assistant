<template>
  <div class="px-4 md:px-6 py-3">
    <div class="max-w-4xl mx-auto flex gap-4 items-center">
      <!-- Spacer matches MessageBubble avatar column (w-8 + gap-4) -->
      <div class="w-8 flex-shrink-0" aria-hidden="true" />
      <div role="status" aria-live="polite" aria-atomic="true" class="flex items-center gap-2">
        <div class="flex items-center gap-1 rounded-2xl bg-muted px-4 py-3">
          <span class="sr-only">Assistant is thinking…</span>
          <span aria-hidden="true" class="h-2 w-2 rounded-full bg-muted-foreground animate-bounce motion-reduce:animate-none" style="animation-delay: 0ms" />
          <span aria-hidden="true" class="h-2 w-2 rounded-full bg-muted-foreground animate-bounce motion-reduce:animate-none" style="animation-delay: 150ms" />
          <span aria-hidden="true" class="h-2 w-2 rounded-full bg-muted-foreground animate-bounce motion-reduce:animate-none" style="animation-delay: 300ms" />
        </div>
      </div>
    </div>
  </div>
</template>
