<script setup>
import { onMounted, computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { settingsApi } from '@/services/api'
import Card from '@/components/ui/Card.vue'

const route = useRoute()

const guildId = computed(() => route.params.guildId)

const auditLogs = ref([])
const loading = ref(false)

// Action icons - returns icon type for template rendering
const getActionIconType = (action) => {
  const actionLower = action.toLowerCase()
  if (actionLower.includes('enabled') || actionLower.includes('added') || actionLower.includes('updated')) {
    return 'check'
  } else if (actionLower.includes('disabled') || actionLower.includes('removed')) {
    return 'x'
  } else if (actionLower.includes('deleted')) {
    return 'trash'
  } else if (actionLower.includes('created')) {
    return 'plus'
  }
  return 'edit'
}

const getActionColor = (action) => {
  const actionLower = action.toLowerCase()
  if (actionLower.includes('enabled') || actionLower.includes('added') || actionLower.includes('updated')) {
    return 'text-green-400'
  } else if (actionLower.includes('disabled') || actionLower.includes('removed')) {
    return 'text-red-400'
  } else if (actionLower.includes('deleted')) {
    return 'text-orange-400'
  }
  return 'text-blue-400'
}

const getCategoryIconType = (category) => {
  const icons = {
    'general': 'cog',
    'chatbot': 'chat',
    'leveling': 'trending-up',
    'music': 'music',
    'moderation': 'shield',
    'welcome': 'hand-wave'
  }
  return icons[category] || 'document'
}

const getCategoryName = (category) => {
  const names = {
    'general': 'General',
    'chatbot': 'Chatbot',
    'leveling': 'Leveling',
    'music': 'Music',
    'moderation': 'Moderation',
    'welcome': 'Welcome'
  }
  return names[category] || category
}

const formatTimestamp = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleString('id-ID', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

onMounted(() => {
  loadAuditLogs()
})

async function loadAuditLogs() {
  loading.value = true
  try {
    const response = await settingsApi.getAuditLogs(guildId.value, 100)
    auditLogs.value = response.data || []
  } catch (error) {
    console.error('Failed to load audit logs:', error)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 bg-gradient-to-br from-discord-yellow to-orange-500 rounded-xl flex items-center justify-center shadow-lg">
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
        </div>
        <div>
          <h2 class="text-xl font-bold text-white">Audit Logs</h2>
          <p class="text-discord-text-secondary text-sm">Riwayat perubahan pengaturan server</p>
        </div>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="text-center py-12">
      <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-discord-blurple"></div>
      <p class="text-discord-text-secondary mt-4">Memuat audit logs...</p>
    </div>

    <!-- Audit logs list -->
    <div v-else-if="auditLogs.length > 0" class="space-y-3">
      <div
        v-for="log in auditLogs"
        :key="log.id"
        class="bg-discord-bg-secondary rounded-lg p-4 border-l-4"
        :class="{
          'border-green-500': log.action.toLowerCase().includes('enabled') || log.action.toLowerCase().includes('added') || log.action.toLowerCase().includes('updated'),
          'border-red-500': log.action.toLowerCase().includes('disabled') || log.action.toLowerCase().includes('removed'),
          'border-orange-500': log.action.toLowerCase().includes('deleted'),
          'border-blue-500': !log.action.toLowerCase().includes('enabled') && !log.action.toLowerCase().includes('disabled') && !log.action.toLowerCase().includes('added') && !log.action.toLowerCase().includes('removed') && !log.action.toLowerCase().includes('deleted')
        }"
      >
        <div class="flex items-start gap-4">
          <!-- Action icon -->
          <div class="flex-shrink-0" :class="getActionColor(log.action)">
            <!-- Check Icon -->
            <svg v-if="getActionIconType(log.action) === 'check'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <!-- X Icon -->
            <svg v-else-if="getActionIconType(log.action) === 'x'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <!-- Trash Icon -->
            <svg v-else-if="getActionIconType(log.action) === 'trash'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
            </svg>
            <!-- Plus Icon -->
            <svg v-else-if="getActionIconType(log.action) === 'plus'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <!-- Edit Icon (default) -->
            <svg v-else class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
            </svg>
          </div>

          <!-- Content -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-sm text-discord-text-muted flex items-center gap-1">
                <!-- Category Icons -->
                <svg v-if="getCategoryIconType(log.category) === 'cog'" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                </svg>
                <svg v-else-if="getCategoryIconType(log.category) === 'chat'" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
                </svg>
                <svg v-else-if="getCategoryIconType(log.category) === 'trending-up'" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
                </svg>
                <svg v-else-if="getCategoryIconType(log.category) === 'music'" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"/>
                </svg>
                <svg v-else-if="getCategoryIconType(log.category) === 'shield'" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
                </svg>
                <svg v-else-if="getCategoryIconType(log.category) === 'hand-wave'" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 11.5V14m0-2.5v-6a1.5 1.5 0 113 0m-3 6a1.5 1.5 0 00-3 0v2a7.5 7.5 0 0015 0v-5a1.5 1.5 0 00-3 0m-6-3V11m0-5.5v-1a1.5 1.5 0 013 0v1m0 0V11m0-5.5a1.5 1.5 0 013 0v3m0 0V11"/>
                </svg>
                <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
                {{ getCategoryName(log.category) }}
              </span>
              <span class="font-medium" :class="getActionColor(log.action)">
                {{ log.action }}
              </span>
            </div>

            <!-- Details -->
            <p v-if="log.details" class="text-sm text-discord-text-secondary mt-1">
              {{ log.details }}
            </p>

            <!-- User and time -->
            <div class="flex items-center gap-4 mt-2 text-xs text-discord-text-muted">
              <span class="flex items-center gap-1">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
                </svg>
                {{ log.user_name }}
              </span>
              <span class="flex items-center gap-1">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                {{ formatTimestamp(log.timestamp) }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="text-center py-12">
      <div class="mb-4 flex justify-center">
        <svg class="w-16 h-16 text-discord-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
        </svg>
      </div>
      <h3 class="text-lg font-semibold text-white mb-2">Belum ada log</h3>
      <p class="text-discord-text-secondary">
        Belum ada perubahan yang dilakukan di server ini.
      </p>
    </div>
  </div>
</template>
