import { render, type RenderOptions } from '@testing-library/vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory, type Router } from 'vue-router'
import { routes } from '@/router'
import type { Component } from 'vue'

export interface RenderWithProvidersOptions extends Omit<RenderOptions, 'global'> {
  initialRoute?: string
}

export function renderWithProviders(
  component: Component,
  options: RenderWithProvidersOptions = {},
): ReturnType<typeof render> & { router: Router } {
  const { initialRoute = '/', ...renderOptions } = options

  const pinia = createPinia()
  const router = createRouter({
    history: createWebHistory(),
    routes,
  })

  if (initialRoute !== '/') {
    router.push(initialRoute)
  }

  const result = render(component, {
    ...renderOptions,
    global: {
      plugins: [pinia, router],
    },
  })

  return { ...result, router }
}
