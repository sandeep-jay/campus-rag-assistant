import client from './client'
import type { User, LoginResponse, RegisterResponse } from './types'

export interface LoginCredentials {
  username: string
  password: string
}

export interface RegisterCredentials {
  username: string
  email: string
  password: string
}

export async function loginJson(credentials: LoginCredentials): Promise<LoginResponse> {
  const { data } = await client.post<LoginResponse>('/api/auth/login-json', credentials)
  return data
}

export async function logout(): Promise<void> {
  await client.post('/api/auth/logout')
}

export async function register(credentials: RegisterCredentials): Promise<RegisterResponse> {
  const { data } = await client.post<RegisterResponse>('/api/auth/register', credentials)
  return data
}

export async function getMe(): Promise<User> {
  const { data } = await client.get<User>('/api/auth/me')
  return data
}
