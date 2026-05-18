import { mergeConfig, defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'
import { sharedViteUserConfig } from './vite.shared.config'

export default mergeConfig(
  sharedViteUserConfig(),
  defineConfig({
    plugins: [tailwindcss()],
    server: {
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
          cookieDomainRewrite: '',
        },
      },
    },
  }),
)
