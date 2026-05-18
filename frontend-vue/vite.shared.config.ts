import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'
import type { UserConfig } from 'vite'

/** Shared between app dev/build and Vitest (no Tailwind native Oxide plugin). */
export function sharedViteUserConfig(): UserConfig {
  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
  }
}
