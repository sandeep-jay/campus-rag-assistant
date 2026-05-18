import { setupWorker } from 'msw/browser'
import { handlers } from './handlers'

/** Dev-only worker; started from src/main.ts when VITE_ENABLE_MSW=true */
export const worker = setupWorker(...handlers)
