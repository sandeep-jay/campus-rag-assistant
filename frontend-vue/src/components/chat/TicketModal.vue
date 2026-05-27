<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { AlertTriangle, X } from 'lucide-vue-next'
import { useChatStore } from '@/stores/chat'
import { useHelpdeskStore } from '@/stores/helpdesk'
import type { TicketDraft } from '@/types/helpdesk'

const helpdesk = useHelpdeskStore()
const chat = useChatStore()
const form = ref<TicketDraft | null>(null)
const dialog = ref<HTMLDivElement | null>(null)
const titleId = 'helpdesk-modal-title'

watch(
  () => helpdesk.draft,
  (next) => {
    form.value = next ? { ...next } : null
  },
  { immediate: true },
)

watch(
  () => helpdesk.modalOpen,
  async (open) => {
    if (!open) return
    await nextTick()
    const root = dialog.value
    if (!root) return
    const firstFocusable = root.querySelector<HTMLElement>(
      'input, textarea, select, button, [tabindex]:not([tabindex="-1"])',
    )
    firstFocusable?.focus()
  },
  { immediate: true },
)

function isVisible(el: HTMLElement): boolean {
  return !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length)
}

function focusableEls(): HTMLElement[] {
  const root = dialog.value
  if (!root) return []
  const selector = [
    'a[href]',
    'button:not([disabled])',
    'input:not([disabled])',
    'textarea:not([disabled])',
    'select:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
  ].join(', ')
  return Array.from(root.querySelectorAll<HTMLElement>(selector)).filter(isVisible)
}

function onKeydown(event: KeyboardEvent): void {
  if (!helpdesk.modalOpen) return
  if (event.key === 'Escape') {
    event.stopPropagation()
    helpdesk.closeModal()
    return
  }
  if (event.key !== 'Tab') return
  const focusables = focusableEls()
  if (focusables.length === 0) return
  const first = focusables[0]
  const last = focusables[focusables.length - 1]
  const active = document.activeElement as HTMLElement | null
  if (event.shiftKey && (active === first || !active)) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && active === last) {
    event.preventDefault()
    first.focus()
  }
}

window.addEventListener('keydown', onKeydown)
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

const submitting = computed(() => helpdesk.submitting)

async function handleSubmit(): Promise<void> {
  if (!form.value) return
  const result = await helpdesk.submitIssue(form.value)
  if (result) {
    const verb = result.deduplicated ? 'is already' : 'was'
    chat.addAssistantMessage(
      `Issue #${result.issue_number} ${verb} filed.\n\n[View on GitHub](${result.issue_url})`,
    )
    helpdesk.reset()
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="helpdesk.modalOpen"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
      role="presentation"
      data-testid="helpdesk-modal-overlay"
      @click.self="helpdesk.closeModal"
    >
      <div
        ref="dialog"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        class="w-full max-w-lg rounded-lg border border-border bg-card text-foreground shadow-xl"
        data-testid="helpdesk-modal"
      >
        <div class="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
          <h2 :id="titleId" class="text-chat-display">Review support ticket</h2>
          <button
            type="button"
            class="rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label="Close ticket review"
            @click="helpdesk.closeModal"
          >
            <X class="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        <p
          class="mx-5 mt-4 flex items-start gap-2 rounded-md border border-warning-subtle bg-warning-subtle px-3 py-2 text-chat-caption text-warning-subtle-foreground"
          role="note"
          data-testid="helpdesk-sensitive-warning"
        >
          <AlertTriangle class="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          <span>
            AI-generated draft. <strong>Review carefully and remove any sensitive
            information</strong> (names, emails, secrets, IDs) before submitting.
          </span>
        </p>

        <div v-if="form" class="px-5 py-4 space-y-4">
          <div class="space-y-1">
            <label for="hd-title" class="text-chat-label">Title</label>
            <input
              id="hd-title"
              v-model="form.title"
              type="text"
              maxlength="120"
              class="w-full rounded-md border border-border bg-background px-3 py-2 text-chat-body focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>

          <div class="space-y-1">
            <label for="hd-description" class="text-chat-label">Description</label>
            <textarea
              id="hd-description"
              v-model="form.description"
              rows="4"
              class="w-full rounded-md border border-border bg-background px-3 py-2 text-chat-body focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div class="space-y-1">
              <label for="hd-severity" class="text-chat-label">Severity</label>
              <select
                id="hd-severity"
                v-model="form.severity"
                class="w-full rounded-md border border-border bg-background px-3 py-2 text-chat-body focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
            <div class="space-y-1">
              <label for="hd-category" class="text-chat-label">Category</label>
              <select
                id="hd-category"
                v-model="form.category"
                class="w-full rounded-md border border-border bg-background px-3 py-2 text-chat-body focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <option value="network">Network</option>
                <option value="access">Access</option>
                <option value="application">Application</option>
                <option value="hardware">Hardware</option>
                <option value="account">Account</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>

          <div class="space-y-1">
            <label for="hd-impact" class="text-chat-label">Impact</label>
            <select
              id="hd-impact"
              v-model="form.impact"
              class="w-full rounded-md border border-border bg-background px-3 py-2 text-chat-body focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option value="Single user">Single user</option>
              <option value="Team">Team</option>
              <option value="Campus-wide">Campus-wide</option>
            </select>
          </div>

          <div class="space-y-1">
            <label for="hd-steps" class="text-chat-label">
              Steps to reproduce <span class="text-muted-foreground">(optional)</span>
            </label>
            <textarea
              id="hd-steps"
              v-model="form.steps_to_reproduce"
              rows="2"
              class="w-full rounded-md border border-border bg-background px-3 py-2 text-chat-body focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>

          <p
            v-if="helpdesk.error"
            class="text-chat-caption text-red-700 dark:text-red-300"
            role="alert"
          >
            {{ helpdesk.error }}
          </p>
        </div>

        <div class="flex items-center justify-end gap-2 border-t border-border px-5 py-3">
          <button
            type="button"
            class="inline-flex items-center rounded-md border border-border px-3 py-1.5 text-chat-ui hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            @click="helpdesk.closeModal"
          >
            Cancel
          </button>
          <button
            type="button"
            class="inline-flex items-center rounded-md bg-primary px-3 py-1.5 text-primary-foreground text-chat-ui hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
            :disabled="submitting"
            @click="handleSubmit"
          >
            <span v-if="submitting">Creating&hellip;</span>
            <span v-else>Create issue</span>
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
