import axios from 'axios'

/**
 * Base axios instance.
 * withCredentials: true is REQUIRED for httpOnly cookie auth to work cross-origin.
 * The 401 interceptor is wired in main.ts after router + pinia are created,
 * to avoid circular dependency (stores → client → stores).
 */
const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

export default client
