<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useGuildStore } from '@/stores/guild'
import { useAuthStore } from '@/stores/auth'
import { useLocaleStore } from '@/stores/locale'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: true
  },
  isMobile: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close'])

const router = useRouter()
const route = useRoute()
const guildStore = useGuildStore()
const authStore = useAuthStore()
const localeStore = useLocaleStore()

const tabs = computed(() => [
  { name: localeStore.t('sidebar.general'), icon: 'cog', path: 'overview' },
  { name: localeStore.t('sidebar.leveling'), icon: 'trending-up', path: 'leveling' },
  { name: localeStore.t('sidebar.chatbot'), icon: 'chat', path: 'chatbot' },
  { name: localeStore.t('sidebar.music'), icon: 'music', path: 'music' },
  { name: localeStore.t('sidebar.moderation'), icon: 'shield', path: 'moderation' },
  { name: localeStore.t('sidebar.logs'), icon: 'document', path: 'logs' },
  { name: localeStore.t('sidebar.settings'), icon: 'settings', path: 'settings' }
])

const activeTab = computed(() => {
  return route.name?.split('-')[1] || 'overview'
})

const currentGuild = computed(() => {
  return guildStore.manageableGuilds.find(g => String(g.id) === String(guildStore.selectedGuildId))
})

const currentGuildIcon = computed(() => {
  return currentGuild.value ? guildStore.getGuildIcon(currentGuild.value) : null
})

function navigateToTab(tabPath) {
  if (guildStore.selectedGuildId) {
    router.push(`/dashboard/${guildStore.selectedGuildId}/${tabPath}`)
    // Close sidebar on mobile after navigation
    if (props.isMobile) {
      emit('close')
    }
  }
}

function goToServerSelect() {
  router.push('/servers')
  if (props.isMobile) {
    emit('close')
  }
}

function logout() {
  authStore.logout()
  router.push('/')
}

function onImageError(event) {
  // Fallback to initial if image fails to load
  event.target.style.display = 'none'
  const next = event.target.nextElementSibling
  if (next) {
    next.style.display = 'flex'
  }
}

function closeSidebar() {
  emit('close')
}
</script>

<template>
  <div class="sidebar-wrapper">
    <!-- Mobile Backdrop Overlay -->
    <Transition name="fade">
      <div 
        v-if="isMobile && isOpen" 
        class="fixed inset-0 bg-black/50 z-40 lg:hidden"
        @click="closeSidebar"
      ></div>
    </Transition>

    <!-- Sidebar -->
    <aside 
      v-show="isOpen"
      class="w-64 bg-discord-bg-secondary border-r border-discord-bg-primary flex flex-col h-full"
      :class="{
        'fixed inset-y-0 left-0 z-50 shadow-2xl': isMobile,
        'relative': !isMobile
      }"
    >
    <!-- Header with back button -->
    <div class="p-4 border-b border-discord-bg-primary">
      <button
        @click="goToServerSelect"
        class="flex items-center gap-2 text-discord-text-secondary hover:text-discord-text-primary transition-colors mb-4 text-sm"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
        </svg>
        Back to Servers
      </button>
      <div class="flex items-center gap-3">
        <div class="relative">
          <img
            v-if="currentGuildIcon"
            :src="currentGuildIcon"
            class="w-10 h-10 rounded-full object-cover"
            @error="onImageError"
          />
          <div
            v-show="!currentGuildIcon"
            class="w-10 h-10 bg-discord-blurple rounded-full flex items-center justify-center text-lg font-bold absolute top-0 left-0"
          >
            {{ currentGuild?.name.charAt(0) || '?' }}
          </div>
        </div>
        <div class="flex-1 min-w-0">
          <h2 class="font-semibold text-white truncate">{{ currentGuild?.name || 'Server' }}</h2>
          <p class="text-xs text-discord-text-secondary">Settings</p>
        </div>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="flex-1 overflow-y-auto p-3">
      <nav class="space-y-1">
        <button
          v-for="tab in tabs"
          :key="tab.path"
          @click="navigateToTab(tab.path)"
          class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors text-left"
          :class="{
            'bg-discord-bg-tertiary text-white': activeTab === tab.path,
            'text-discord-text-secondary hover:bg-discord-bg-tertiary hover:text-discord-text-primary': activeTab !== tab.path
          }"
        >
          <!-- Cog Icon (General/Settings) -->
          <svg v-if="tab.icon === 'cog'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
          </svg>
          <!-- Home Icon -->
          <svg v-else-if="tab.icon === 'home'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
          </svg>
          <!-- Trending Up Icon (Leveling) -->
          <svg v-else-if="tab.icon === 'trending-up'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
          </svg>
          <!-- Chat Icon (Chatbot) -->
          <svg v-else-if="tab.icon === 'chat'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
          </svg>
          <!-- Music Icon -->
          <svg v-else-if="tab.icon === 'music'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"/>
          </svg>
          <!-- Shield Icon (Moderation) -->
          <svg v-else-if="tab.icon === 'shield'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
          </svg>
          <!-- Document Icon (Logs) -->
          <svg v-else-if="tab.icon === 'document'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
          <!-- Settings Icon -->
          <svg v-else-if="tab.icon === 'settings'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"/>
          </svg>
          <span class="font-medium">{{ tab.name }}</span>
        </button>
      </nav>
    </div>

    <!-- User Info -->
    <div class="p-4 border-t border-discord-bg-primary">
      <div class="flex items-center justify-between">
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
          <span class="text-discord-text-primary text-sm truncate">{{ authStore.user?.username || 'User' }}</span>
        </div>
        <button
          @click="logout"
          class="text-discord-text-secondary hover:text-discord-red transition-colors text-xs"
          title="Logout"
        >
          Logout
        </button>
      </div>
    </div>
  </aside>
  </div>
</template>

