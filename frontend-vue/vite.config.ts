import { mergeConfig, defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'
import { sharedViteUserConfig } from './vite.shared.config'

export default mergeConfig(
  sharedViteUserConfig(),
  defineConfig({
    plugins: [tailwindcss()],
    server: {
      host: '127.0.0.1',
      port: 5173,
      strictPort: true,
      proxy: {
        '/api/chat/stream': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
          cookieDomainRewrite: '',
          proxyTimeout: 0,
          configure: (proxy) => {
            proxy.on('proxyRes', (proxyRes) => {
              delete proxyRes.headers['content-encoding']
              proxyRes.headers['cache-control'] = 'no-cache'
            })
          },
        },
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
          cookieDomainRewrite: '',
          configure: (proxy) => {
            proxy.on('proxyRes', (proxyRes) => {
              if (proxyRes.headers['content-type']?.includes('text/event-stream')) {
                delete proxyRes.headers['content-encoding']
              }
            })
          },
        },
      },
    },
  }),
)
