<script setup>
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useGuildStore } from '@/stores/guild'

const authStore = useAuthStore()
const guildStore = useGuildStore()

const emit = defineEmits(['logout'])

defineProps({
  title: {
    type: String,
    default: 'Dashboard'
  }
})
</script>

<template>
  <header class="h-14 bg-discord-bg-secondary border-b border-discord-bg-primary flex items-center justify-between px-6">
    <h1 class="font-semibold text-lg text-white">
      {{ guildStore.selectedGuild?.name || 'Dashboard' }}
    </h1>

    <div class="flex items-center gap-4">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 bg-discord-blurple rounded-full flex items-center justify-center text-sm font-semibold">
          {{ authStore.userInitial }}
        </div>
        <span class="text-discord-text-primary font-medium">{{ authStore.user?.username || 'User' }}</span>
      </div>

      <button
        @click="emit('logout')"
        class="px-3 py-1.5 text-sm border border-discord-red text-discord-red rounded hover:bg-discord-red hover:text-white transition-colors"
      >
        Logout
      </button>
    </div>
  </header>
</template>
