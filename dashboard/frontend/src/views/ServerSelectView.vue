<script setup>
import { onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useGuildStore } from '@/stores/guild'
import Button from '@/components/ui/Button.vue'

const router = useRouter()
const authStore = useAuthStore()
const guildStore = useGuildStore()

const manageableGuilds = computed(() => guildStore.manageableGuilds)

onMounted(async () => {
  // Clear any selected guild to prevent auto-redirect
  guildStore.clearSelectedGuild()
  localStorage.removeItem('selected_guild_id')

  // Only load guilds, don't auto-select
  await guildStore.loadGuilds()
})

function selectGuild(guildId) {
  guildStore.selectGuild(guildId)
  router.push(`/dashboard/${guildId}`)
}

function logout() {
  authStore.logout()
  router.push('/')
}

function getGuildIcon(guild) {
  return guildStore.getGuildIcon(guild)
}

function onImageError(event) {
  event.target.style.display = 'none'
  const next = event.target.nextElementSibling
  if (next) {
    next.style.display = 'flex'
  }
}
</script>

<template>
  <div class="min-h-screen bg-discord-bg-primary flex flex-col">
    <!-- Header -->
    <header class="h-14 bg-discord-bg-secondary border-b border-discord-bg-primary flex items-center justify-between px-6">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 bg-discord-blurple rounded-full flex items-center justify-center text-sm font-bold">
          N
        </div>
        <span class="font-semibold text-white">Nothing Bot Dashboard</span>
      </div>
      <div class="flex items-center gap-4">
        <div class="flex items-center gap-2">
          <div class="relative">
            <img
              v-if="authStore.userAvatar"
              :src="authStore.userAvatar"
              class="w-8 h-8 rounded-full object-cover"
              @error="onImageError"
            />
            <div
              v-show="!authStore.userAvatar"
              class="w-8 h-8 bg-discord-blurple rounded-full flex items-center justify-center text-xs font-semibold absolute top-0 left-0"
            >
              {{ authStore.userInitial }}
            </div>
          </div>
          <span class="text-discord-text-primary text-sm">{{ authStore.user?.username || 'User' }}</span>
        </div>
        <button
          @click="logout"
          class="px-3 py-1.5 text-xs border border-discord-red text-discord-red rounded hover:bg-discord-red hover:text-white transition-colors"
        >
          Logout
        </button>
      </div>
    </header>

    <!-- Server List -->
    <main class="flex-1 flex items-center justify-center p-8">
      <div v-if="manageableGuilds.length === 0" class="text-center">
        <p class="text-discord-text-secondary mb-4">No servers found</p>
        <p class="text-discord-text-muted text-sm">Make sure the bot is in your server and you have Administrator permission.</p>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 w-full max-w-4xl">
        <div
          v-for="guild in manageableGuilds"
          :key="guild.id"
          @click="selectGuild(guild.id)"
          class="bg-discord-bg-secondary p-6 rounded-xl cursor-pointer hover:bg-discord-bg-tertiary transition-colors group"
        >
          <div class="flex items-center gap-4">
            <div class="relative flex-shrink-0">
              <img
                v-if="getGuildIcon(guild)"
                :src="getGuildIcon(guild)"
                class="w-16 h-16 rounded-full object-cover"
                @error="onImageError"
              />
              <div
                v-show="!getGuildIcon(guild)"
                class="w-16 h-16 bg-discord-bg-tertiary rounded-full flex items-center justify-center text-xl font-bold absolute top-0 left-0 group-hover:bg-discord-blurple transition-colors"
              >
                {{ guild.name.charAt(0) }}
              </div>
            </div>
            <div class="flex-1 min-w-0">
              <h3 class="font-semibold text-white truncate">{{ guild.name }}</h3>
              <p class="text-discord-text-secondary text-sm">ID: {{ guild.id }}</p>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>
