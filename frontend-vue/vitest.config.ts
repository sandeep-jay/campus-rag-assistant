import { fileURLToPath } from 'node:url'
import { mergeConfig, defineConfig, configDefaults } from 'vitest/config'
import { sharedViteUserConfig } from './vite.shared.config'

export default mergeConfig(
  sharedViteUserConfig(),
  defineConfig({
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
      exclude: [...configDefaults.exclude, 'e2e/**'],
      root: fileURLToPath(new URL('./', import.meta.url)),
      coverage: {
        provider: 'v8',
        reporter: ['text', 'html', 'lcov'],
        thresholds: {
          lines: 80,
          functions: 80,
          branches: 75,
          statements: 80,
        },
        exclude: [
          'src/mocks/**',
          'src/test/**',
          'src/lib/**',
          '**/*.test.ts',
          'src/main.ts',
          'src/router/**',
          'e2e/**',
          'playwright.config.ts',
          'vite.config.ts',
          'vite.shared.config.ts',
          'vitest.config.ts',
          'eslint.config.ts',
          'src/api/types.ts',
          'src/api/interceptors.ts',
          'src/App.vue',
          'src/components/layout/**',
          'src/components/sidebar/AppSidebar.vue',
        ],
      },
    },
  }),
)
