<script setup lang="ts">
import { ref } from 'vue'
import LoginForm from '@/components/auth/LoginForm.vue'
import RegisterForm from '@/components/auth/RegisterForm.vue'

const activeTab = ref<'login' | 'register'>('login')
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-background p-4">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <h1 class="text-3xl font-bold text-foreground">BCourses Chatbot</h1>
        <p class="text-muted-foreground mt-2">Your AI-powered course support assistant</p>
      </div>

      <div class="rounded-xl border border-border bg-card shadow-sm">
        <!-- Tab navigation -->
        <div class="flex border-b border-border" role="tablist" aria-label="Authentication options">
          <button
            id="tab-login"
            role="tab"
            :aria-selected="activeTab === 'login'"
            aria-controls="panel-login"
            class="flex-1 px-4 py-3 text-sm font-medium transition-colors"
            :class="activeTab === 'login'
              ? 'text-foreground border-b-2 border-primary'
              : 'text-muted-foreground hover:text-foreground'"
            @click="activeTab = 'login'"
          >
            Sign in
          </button>
          <button
            id="tab-register"
            role="tab"
            :aria-selected="activeTab === 'register'"
            aria-controls="panel-register"
            class="flex-1 px-4 py-3 text-sm font-medium transition-colors"
            :class="activeTab === 'register'
              ? 'text-foreground border-b-2 border-primary'
              : 'text-muted-foreground hover:text-foreground'"
            @click="activeTab = 'register'"
          >
            Create account
          </button>
        </div>

        <!-- Tab panels -->
        <div class="p-6">
          <div
            v-show="activeTab === 'login'"
            id="panel-login"
            role="tabpanel"
            aria-labelledby="tab-login"
          >
            <LoginForm />
          </div>
          <div
            v-show="activeTab === 'register'"
            id="panel-register"
            role="tabpanel"
            aria-labelledby="tab-register"
          >
            <RegisterForm />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
