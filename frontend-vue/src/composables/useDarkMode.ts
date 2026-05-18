import { ref, watchEffect } from 'vue'

// Module-level singleton so dark mode state is shared across all component instances
export const isDark = ref(
  typeof window !== 'undefined'
    ? localStorage.getItem('theme') === 'dark' ||
        (!localStorage.getItem('theme') &&
          window.matchMedia?.('(prefers-color-scheme: dark)').matches)
    : false,
)

export function useDarkMode(): {
  isDark: typeof isDark
  toggle: () => void
} {
  watchEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light')
      localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
    }
  })

  function toggle(): void {
    isDark.value = !isDark.value
  }

  return { isDark, toggle }
}
