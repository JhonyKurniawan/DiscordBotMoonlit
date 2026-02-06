<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useGuildStore } from '@/stores/guild'
import { authApi } from '@/services/api'

const router = useRouter()
const authStore = useAuthStore()
const guildStore = useGuildStore()

onMounted(async () => {
  // Check if user is already logged in
  const isLoggedIn = await authStore.checkAuth()
  if (isLoggedIn) {
    await guildStore.loadGuilds()
    router.push('/dashboard')
  }
})

function login() {
  window.location.href = authApi.getDiscordAuthUrl()
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-discord-bg-primary to-discord-bg-secondary">
    <div class="bg-discord-bg-secondary p-10 rounded-xl shadow-2xl text-center max-w-md w-full mx-4">
      <!-- Bot Logo -->
      <div class="w-16 h-16 bg-discord-blurple rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-4">
        N
      </div>

      <h1 class="text-2xl font-bold text-white mb-2">Nothing Bot Dashboard</h1>
      <p class="text-discord-text-secondary mb-6">Login with Discord to manage your server settings</p>

      <button
        @click="login"
        class="inline-flex items-center gap-3 bg-discord-blurple hover:bg-discord-blurpleHover text-white px-6 py-3 rounded-lg font-medium transition-colors"
      >
        <svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515a.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0a12.64 12.64 0 0 0-.617-1.25a.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057a19.9 19.9 0 0 0 5.993 3.03a.078.078 0 0 0 .084-.028a14.09 14.09 0 0 0 1.226-1.994a.076.076 0 0 0-.041-.106a13.107 13.107 0 0 1-1.872-.892a.077.077 0 0 1-.008-.128a10.2 10.2 0 0 0 .372-.292a.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127a12.299 12.299 0 0 1-1.873.892a.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028a19.839 19.839 0 0 0 6.002-3.03a.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.956-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.955-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.946 2.418-2.157 2.418z"/>
        </svg>
        Login with Discord
      </button>
    </div>
  </div>
</template>
