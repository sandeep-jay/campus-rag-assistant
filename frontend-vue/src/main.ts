import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/main.css'

async function bootstrap(): Promise<void> {
  if (import.meta.env.DEV && import.meta.env.VITE_ENABLE_MSW === 'true') {
    const { worker } = await import('./mocks/browser')
    await worker.start({ onUnhandledRequest: 'bypass' })
  }

  const app = createApp(App)
  const pinia = createPinia()

  app.use(pinia)
  app.use(router)

  void import('./api/interceptors').then(({ setupInterceptors }) => {
    setupInterceptors()
  })

  app.mount('#app')
}

void bootstrap().catch((err: unknown) => {
  console.error('Failed to start app', err)
})
