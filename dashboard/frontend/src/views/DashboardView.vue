<script setup>
import { onMounted, onUnmounted, watch, computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useGuildStore } from '@/stores/guild'
import Sidebar from '@/components/layout/Sidebar.vue'
import StatusMessage from '@/components/ui/StatusMessage.vue'

const route = useRoute()
const guildStore = useGuildStore()

// Sidebar responsive state
const sidebarOpen = ref(true)
const windowWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1024)

const isMobile = computed(() => windowWidth.value < 1024)

// Auto-close sidebar on mobile initially
watch(isMobile, (mobile) => {
  sidebarOpen.value = !mobile
}, { immediate: true })

function toggleSidebar() {
  sidebarOpen.value = !sidebarOpen.value
}

function closeSidebar() {
  if (isMobile.value) {
    sidebarOpen.value = false
  }
}

function handleResize() {
  windowWidth.value = window.innerWidth
}

// Show content if we have guildId in route
const showContent = computed(() => {
  return route.params.guildId !== undefined
})

onMounted(() => {
  window.addEventListener('resize', handleResize)
  
  // Load guilds in background, don't await
  if (guildStore.guilds.length === 0) {
    guildStore.loadGuilds()
  }

  // Set guild from route
  if (route.params.guildId) {
    guildStore.selectGuild(route.params.guildId)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
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
    <!-- Sidebar - hidden on mobile by default, toggleable -->
    <Sidebar 
      :is-open="sidebarOpen" 
      :is-mobile="isMobile"
      @close="closeSidebar"
      class="lg:block"
      :class="{ 'hidden': !sidebarOpen && !isMobile }"
    />

    <!-- Main Content -->
    <div class="flex-1 flex flex-col overflow-hidden min-w-0">
      <!-- Mobile Header with Hamburger -->
      <header 
        v-if="isMobile"
        class="h-14 bg-discord-bg-secondary border-b border-discord-bg-primary flex items-center justify-between px-4 shrink-0"
      >
        <button
          @click="toggleSidebar"
          class="p-2 rounded-lg text-discord-text-secondary hover:text-white hover:bg-discord-bg-tertiary transition-colors"
          aria-label="Toggle menu"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
          </svg>
        </button>
        <span class="font-semibold text-white truncate">{{ guildStore.selectedGuild?.name || 'Dashboard' }}</span>
        <div class="w-10"></div> <!-- Spacer for centering -->
      </header>

      <!-- Content -->
      <main class="flex-1 overflow-y-auto p-4 lg:p-6">
        <StatusMessage />

        <router-view v-if="showContent" />
        <div v-else class="flex items-center justify-center h-full">
          <p class="text-discord-text-secondary">Select a server to manage its settings</p>
        </div>
      </main>
    </div>
  </div>
</template>
