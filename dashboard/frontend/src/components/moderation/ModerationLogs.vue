<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { settingsApi } from '@/services/api'

const props = defineProps({
  guildId: {
    type: [String, Number],
    required: true
  }
})

// State
const logs = ref([])
const loading = ref(false)
const currentPage = ref(0)
const logsPerPage = ref(25)
const filterType = ref('')

// Action types for filter
const actionTypes = [
  { value: '', label: 'All Actions' },
  { value: 'ban', label: 'Ban' },
  { value: 'kick', label: 'Kick' },
  { value: 'timeout', label: 'Timeout' },
  { value: 'unban', label: 'Unban' },
  { value: 'warn', label: 'Warning' }
]

// Get action badge styles
function getActionBadge(action) {
  const badges = {
    'ban': { text: 'BAN', class: 'bg-red-500/20 text-red-400' },
    'kick': { text: 'KICK', class: 'bg-orange-500/20 text-orange-400' },
    'timeout': { text: 'TIMEOUT', class: 'bg-yellow-500/20 text-yellow-400' },
    'unban': { text: 'UNBAN', class: 'bg-green-500/20 text-green-400' },
    'warn': { text: 'WARN', class: 'bg-purple-500/20 text-purple-400' }
  }
  return badges[action?.toLowerCase()] || { text: action?.toUpperCase() || 'ACTION', class: 'bg-discord-bg-tertiary text-discord-text-secondary' }
}

// Filtered logs
const filteredLogs = computed(() => {
  if (!filterType.value) return logs.value
  return logs.value.filter(log => log.action?.toLowerCase() === filterType.value)
})

// Paginated logs
const totalPages = computed(() => Math.ceil(filteredLogs.value.length / logsPerPage.value))
const paginatedLogs = computed(() => {
  const start = currentPage.value * logsPerPage.value
  const end = start + logsPerPage.value
  return filteredLogs.value.slice(start, end)
})

// Load moderation logs
async function loadLogs() {
  loading.value = true
  try {
    const response = await settingsApi.getModerationLogs(props.guildId)
    if (response.data) {
      logs.value = response.data.logs || []
    }
  } catch (error) {
    console.error('Failed to load moderation logs:', error)
    logs.value = []
  } finally {
    loading.value = false
  }
}

// Format date
function formatDate(dateString) {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleDateString('id-ID', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Format relative time
function formatRelativeTime(dateString) {
  if (!dateString) return ''
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)
  
  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return formatDate(dateString)
}

watch(() => props.guildId, () => {
  currentPage.value = 0
  loadLogs()
})

onMounted(() => {
  loadLogs()
})
</script>

<template>
  <div class="space-y-4">
    <!-- Filter Bar -->
    <div class="flex items-center gap-3">
      <div class="flex-1 flex gap-2">
        <button
          v-for="type in actionTypes"
          :key="type.value"
          @click="filterType = type.value; currentPage = 0"
          class="px-3 py-1.5 text-xs font-medium rounded-lg transition-all duration-200"
          :class="filterType === type.value 
            ? 'bg-discord-blurple text-white' 
            : 'bg-discord-bg-tertiary text-discord-text-secondary hover:bg-discord-bg-hover hover:text-white'"
        >
          {{ type.label }}
        </button>
      </div>
      <button 
        @click="loadLogs" 
        class="p-2 rounded-lg bg-discord-bg-tertiary hover:bg-discord-bg-hover transition-colors"
        :class="{ 'animate-spin': loading }"
      >
        <svg class="w-4 h-4 text-discord-text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
        </svg>
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-12">
      <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-discord-blurple"></div>
      <p class="text-discord-text-secondary mt-4">Memuat logs...</p>
    </div>

    <!-- Logs List -->
    <div v-else-if="paginatedLogs.length > 0" class="space-y-2">
      <div
        v-for="(log, index) in paginatedLogs"
        :key="index"
        class="flex items-start gap-4 bg-discord-bg-secondary rounded-lg p-4 hover:bg-discord-bg-tertiary transition-colors"
      >
        <!-- Action Badge -->
        <div class="flex-shrink-0">
          <span 
            class="px-2.5 py-1 text-xs font-bold rounded-md"
            :class="getActionBadge(log.action).class"
          >
            {{ getActionBadge(log.action).text }}
          </span>
        </div>

        <!-- Log Details -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 flex-wrap">
            <span class="font-medium text-white">{{ log.target_name || log.target_id || 'Unknown User' }}</span>
            <span class="text-discord-text-muted text-sm">by</span>
            <span class="text-discord-blurple font-medium">{{ log.moderator_name || log.moderator_id || 'Unknown' }}</span>
          </div>
          <p v-if="log.reason" class="text-sm text-discord-text-secondary mt-1 line-clamp-2">
            {{ log.reason }}
          </p>
          <p v-else class="text-sm text-discord-text-muted italic mt-1">
            No reason provided
          </p>
          <div v-if="log.duration" class="text-xs text-discord-text-muted mt-1">
            Duration: {{ log.duration }}
          </div>
        </div>

        <!-- Timestamp -->
        <div class="flex-shrink-0 text-right">
          <p class="text-sm text-discord-text-secondary">{{ formatRelativeTime(log.created_at) }}</p>
          <p class="text-xs text-discord-text-muted">{{ formatDate(log.created_at) }}</p>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="text-center py-12 text-discord-text-tertiary">
      <svg class="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
      </svg>
      <p class="font-medium text-lg">No moderation logs found</p>
      <p class="text-sm mt-1">Moderation actions will appear here</p>
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="flex items-center justify-center gap-4 pt-4">
      <button
        @click="currentPage--"
        :disabled="currentPage === 0"
        class="px-4 py-2 text-sm font-medium rounded-lg bg-discord-bg-tertiary text-discord-text-primary hover:bg-discord-bg-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        Previous
      </button>
      <span class="text-discord-text-secondary text-sm">
        Page {{ currentPage + 1 }} of {{ totalPages }}
      </span>
      <button
        @click="currentPage++"
        :disabled="currentPage >= totalPages - 1"
        class="px-4 py-2 text-sm font-medium rounded-lg bg-discord-bg-tertiary text-discord-text-primary hover:bg-discord-bg-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        Next
      </button>
    </div>
  </div>
</template>
