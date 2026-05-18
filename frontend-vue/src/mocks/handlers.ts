import { http, HttpResponse } from 'msw'

// Use full URLs so handlers work in both Node (Vitest) and browser environments.
// Vitest sends requests to http://localhost:8000 (VITE_API_URL from .env.test).
const BASE = 'http://localhost:8000'

const mockSession = {
  id: 1,
  title: 'Test Chat',
  created_at: new Date().toISOString(),
}

const mockMessages = [
  { id: 1, content: 'Hello', role: 'user', created_at: new Date().toISOString() },
  {
    id: 2,
    content: 'Hi there! How can I help?',
    role: 'assistant',
    metadata: { sources: [], document_contents: [] },
    created_at: new Date().toISOString(),
  },
]

export const handlers = [
  http.post(`${BASE}/api/auth/login-json`, () =>
    HttpResponse.json({ user_id: 1, username: 'testuser', status: 'success' }),
  ),

  http.get(`${BASE}/api/auth/me`, () =>
    HttpResponse.json({ id: 1, username: 'testuser', email: 'test@test.com' }),
  ),

  http.post(`${BASE}/api/auth/logout`, () => HttpResponse.json({ status: 'success' })),

  http.post(`${BASE}/api/auth/register`, () =>
    HttpResponse.json({ message: 'User registered successfully' }),
  ),

  http.get(`${BASE}/api/chat/sessions`, () => HttpResponse.json([mockSession])),

  http.post(`${BASE}/api/chat/sessions`, () => HttpResponse.json(mockSession)),

  http.get(`${BASE}/api/chat/sessions/:id`, () =>
    HttpResponse.json({ ...mockSession, messages: mockMessages }),
  ),

  http.delete(`${BASE}/api/chat/sessions/:id`, () =>
    HttpResponse.json({ message: 'Chat session deleted successfully' }),
  ),

  http.post(`${BASE}/api/chat/stream`, () =>
    new HttpResponse(null, { status: 404 }),
  ),
  http.post(`${BASE}/api/chat/chat`, () =>
    HttpResponse.json({
      session_id: 1,
      user_message: { id: 3, content: 'Hello', role: 'user', created_at: new Date().toISOString() },
      assistant_message: {
        id: 4,
        content: 'Hi! I can help you with that.',
        role: 'assistant',
        metadata: { sources: [], document_contents: [] },
        created_at: new Date().toISOString(),
      },
    }),
  ),

  http.post(`${BASE}/api/chat/feedback`, () =>
    HttpResponse.json({
      id: 1,
      message_id: 2,
      user_id: 1,
      feedback_type: 'thumbs_up',
      rating: null,
      comment: null,
      run_id: null,
      created_at: new Date().toISOString(),
    }),
  ),

  http.get(`${BASE}/api/chat/messages/:id/sources`, () =>
    HttpResponse.json({ message_id: 2, document_contents: [], sources: [] }),
  ),
]
