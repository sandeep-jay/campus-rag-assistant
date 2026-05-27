import { setMaxListeners } from 'node:events'
import { beforeAll, afterEach, afterAll } from 'vitest'
import { cleanup } from '@testing-library/vue'
import '@testing-library/jest-dom'
import { server } from '@/mocks/server'

// MSW's Node interceptor can legitimately attach more than the default
// 10 abort listeners during the full Vitest suite.
setMaxListeners(50)

// Start MSW server before all tests
beforeAll(() => {
  server.listen({ onUnhandledRequest: 'warn' })
})

// Reset handlers after each test to prevent test pollution
afterEach(() => {
  server.resetHandlers()
  cleanup()
})

// Stop MSW server after all tests
afterAll(() => {
  server.close()
})
