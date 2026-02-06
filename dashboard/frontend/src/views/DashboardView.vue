<script setup>
import { onMounted, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useGuildStore } from '@/stores/guild'
import Sidebar from '@/components/layout/Sidebar.vue'
import StatusMessage from '@/components/ui/StatusMessage.vue'

const route = useRoute()
const guildStore = useGuildStore()

// Show content if we have guildId in route
const showContent = computed(() => {
  return route.params.guildId !== undefined
})

onMounted(() => {
  // Load guilds in background, don't await
  if (guildStore.guilds.length === 0) {
    guildStore.loadGuilds()
  }

  // Set guild from route
  if (route.params.guildId) {
    guildStore.selectGuild(route.params.guildId)
  }
})

// Watch for guild changes
watch(() => route.params.guildId, (newGuildId) => {
  if (newGuildId && route.name?.startsWith('guild-')) {
    guildStore.selectGuild(newGuildId)
  }
})
</script>

<template>
  <div class="flex h-screen overflow-hidden">
    <!-- Sidebar -->
    <Sidebar />

    <!-- Main Content -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- Content -->
      <main class="flex-1 overflow-y-auto p-6">
        <StatusMessage />

        <router-view v-if="showContent" />
        <div v-else class="flex items-center justify-center h-full">
          <p class="text-discord-text-secondary">Select a server to manage its settings</p>
        </div>
      </main>
    </div>
  </div>
</template>
