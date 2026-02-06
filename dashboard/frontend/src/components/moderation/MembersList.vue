<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useGuildStore } from '@/stores/guild'
import { settingsApi } from '@/services/api'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'

const props = defineProps({
  guildId: {
    type: [String, Number],
    required: true
  }
})

const guildStore = useGuildStore()

// State
const members = ref([])
const loading = ref(false)
const searchQuery = ref('')
const roleFilter = ref('')
const currentPage = ref(0)
const membersPerPage = ref(25)

// Pagination options
const perPageOptions = [
  { value: 10, label: '10 / hal' },
  { value: 25, label: '25 / hal' },
  { value: 50, label: '50 / hal' },
  { value: 100, label: '100 / hal' }
]

// Role options for filter
const roleOptions = computed(() => {
  const roles = guildStore.roles[props.guildId] || []
  return [
    { value: '', label: 'Semua Role' },
    ...roles.map(role => ({
      value: String(role.id),
      label: role.name,
      color: role.color
    }))
  ]
})

// Modal state
const showModal = ref(false)
const selectedUser = ref(null)
const actionType = ref('')
const reason = ref('')
const durationMinutes = ref(60)

// Track avatar load errors
const avatarErrors = ref(new Set())

function handleAvatarError(userId) {
  avatarErrors.value.add(userId)
}

// Computed
const filteredMembers = computed(() => {
  let result = members.value

  // Filter by role
  if (roleFilter.value) {
    result = result.filter(m =>
      m.roles?.some(r => String(r) === String(roleFilter.value))
    )
  }

  // Filter by search query
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(m =>
      m.username?.toLowerCase().includes(query) ||
      m.display_name?.toLowerCase().includes(query)
    )
  }

  return result
})

const totalPages = computed(() => Math.ceil(filteredMembers.value.length / membersPerPage.value))
const paginatedMembers = computed(() => {
  const start = currentPage.value * membersPerPage.value
  const end = start + membersPerPage.value
  return filteredMembers.value.slice(start, end)
})

// Action modal config
const actionConfig = computed(() => {
  switch (actionType.value) {
    case 'ban':
      return {
        title: 'Ban Member',
        description: 'Ban member ini dari server?',
        confirmText: 'Ban',
        showDuration: true,
        showReason: true
      }
    case 'kick':
      return {
        title: 'Kick Member',
        description: 'Kick member ini dari server?',
        confirmText: 'Kick',
        showDuration: false,
        showReason: true
      }
    case 'timeout':
      return {
        title: 'Timeout Member',
        description: 'Timeout member ini?',
        confirmText: 'Timeout',
        showDuration: true,
        showReason: true
      }
    case 'removeTimeout':
      return {
        title: 'Remove Timeout',
        description: 'Hapus timeout dari member ini?',
        confirmText: 'Remove Timeout',
        showDuration: false,
        showReason: false
      }
    default:
      return null
  }
})

// Duration options
const durationOptions = [
  { value: 10, label: '10 menit' },
  { value: 30, label: '30 menit' },
  { value: 60, label: '1 jam' },
  { value: 360, label: '6 jam' },
  { value: 1440, label: '1 hari' },
  { value: 4320, label: '3 hari' },
  { value: 10080, label: '7 hari' }
]

// Get avatar URL - Discord CDN auto-detects format (PNG/GIF) when no extension
function getAvatarUrl(avatarUrl) {
  if (!avatarUrl) return null
  // Remove extension if present to let Discord CDN auto-detect
  return avatarUrl.replace(/\.(png|jpg|jpeg|webp|gif)$/, '')
}

// Load members
async function loadMembers() {
  loading.value = true
  avatarErrors.value.clear() // Reset avatar errors on reload
  try {
    const offset = currentPage.value * membersPerPage.value
    const response = await settingsApi.getMembers(props.guildId, membersPerPage.value, offset, searchQuery.value)
    if (response.data) {
      members.value = response.data.members || []
    }
  } catch (error) {
    console.error('Failed to load members:', error)
  } finally {
    loading.value = false
  }
}

// Open action modal
function openAction(user, action) {
  selectedUser.value = user
  actionType.value = action
  reason.value = ''
  durationMinutes.value = 60
  showModal.value = true
}

// Close modal
function closeModal() {
  showModal.value = false
  selectedUser.value = null
  actionType.value = ''
  reason.value = ''
}

// Execute action
async function executeAction() {
  if (!selectedUser.value) return

  const userId = selectedUser.value.user_id
  let success = false

  try {
    switch (actionType.value) {
      case 'ban':
        await settingsApi.banMember(props.guildId, userId, {
          reason: reason.value,
          delete_message_days: 0
        })
        success = true
        break
      case 'kick':
        await settingsApi.kickMember(props.guildId, userId, {
          reason: reason.value
        })
        success = true
        break
      case 'timeout':
        await settingsApi.timeoutMember(props.guildId, userId, {
          reason: reason.value,
          duration_minutes: durationMinutes.value
        })
        success = true
        break
      case 'removeTimeout':
        await settingsApi.removeTimeout(props.guildId, userId)
        success = true
        break
    }

    if (success) {
      closeModal()
      loadMembers() // Refresh members list
    }
  } catch (error) {
    console.error('Failed to execute action:', error)
    alert(error.response?.data?.error || 'Failed to execute action')
  }
}

// Get status badge
function getStatusBadge(member) {
  if (member.communication_disabled_until) {
    const timeoutEnd = new Date(member.communication_disabled_until)
    if (timeoutEnd > new Date()) {
      return { text: 'Timed Out', color: 'bg-yellow-500/20 text-yellow-400' }
    }
  }
  return null
}

// Format date
function formatDate(dateString) {
  if (! dateString) return 'N/A'
  return new Date(dateString).toLocaleDateString('id-ID', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

// Watch for search, role filter and pagination changes
watch([searchQuery, roleFilter, currentPage, membersPerPage], () => {
  loadMembers()
})

onMounted(() => {
  guildStore.loadRoles(props.guildId)
  loadMembers()
})
</script>

<template>
  <div class="space-y-4">
    <!-- Controls -->
    <div class="grid grid-cols-[1fr_180px_120px] gap-4">
      <Input
        v-model="searchQuery"
        placeholder="Cari user berdasarkan nama/username..."
      />
      <Select
        v-model="roleFilter"
        :options="roleOptions"
      />
      <Select
        v-model.number="membersPerPage"
        :options="perPageOptions"
      />
    </div>

    <!-- Members list -->
    <div v-if="loading" class="text-center py-12">
      <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-discord-blurple"></div>
      <p class="text-discord-text-secondary mt-4">Memuat members...</p>
    </div>

    <div v-else-if="paginatedMembers.length > 0" class="space-y-2">
      <div
        v-for="member in paginatedMembers"
        :key="member.user_id"
        class="flex items-center gap-4 bg-discord-bg-secondary rounded-lg p-3 hover:bg-discord-bg-tertiary transition-colors"
      >
        <!-- Avatar -->
        <div class="w-10 h-10 rounded-full flex-shrink-0 overflow-hidden bg-discord-blurple flex items-center justify-center">
          <img
            v-if="member.avatar && !avatarErrors.has(member.user_id)"
            :src="getAvatarUrl(member.avatar)"
            class="w-10 h-10 rounded-full object-cover"
            @error="handleAvatarError(member.user_id)"
          />
          <span v-else class="text-white font-bold">
            {{ member.display_name?.charAt(0)?.toUpperCase() || '?' }}
          </span>
        </div>

        <!-- User info -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="font-medium text-white truncate" :style="{ color: member.color ? '#' + member.color.toString(16).padStart(6, '0') : '' }">
              {{ member.display_name }}
            </span>
            <span v-if="getStatusBadge(member)" class="px-2 py-0.5 rounded text-xs" :class="getStatusBadge(member).color">
              {{ getStatusBadge(member).text }}
            </span>
          </div>
          <div class="text-sm text-discord-text-secondary">
            @{{ member.username }}
          </div>
          <div v-if="member.role_info && member.role_info.length > 0" class="flex flex-wrap gap-1 mt-1">
            <span
              v-for="role in member.role_info.slice(0, 3)"
              :key="role.id"
              class="text-xs px-1.5 py-0.5 rounded"
              :style="{ backgroundColor: '#' + role.color.toString(16).padStart(6, '0') + '40', color: '#' + role.color.toString(16).padStart(6, '0') }"
            >
              {{ role.name }}
            </span>
            <span v-if="member.role_info.length > 3" class="text-xs text-discord-text-muted">
              +{{ member.role_info.length - 3 }} more
            </span>
          </div>
        </div>

        <!-- Join date -->
        <div class="hidden md:block text-sm text-discord-text-secondary">
          Joined: {{ formatDate(member.joined_at) }}
        </div>

        <!-- Actions -->
        <div class="flex items-center gap-1.5 flex-shrink-0">
          <Button
            v-if="member.communication_disabled_until"
            @click="openAction(member, 'removeTimeout')"
            variant="ghost"
            size="sm"
          >
            Remove Timeout
          </Button>
          <Button
            @click="openAction(member, 'timeout')"
            variant="ghost"
            size="sm"
          >
            Timeout
          </Button>
          <Button
            @click="openAction(member, 'kick')"
            variant="ghost"
            size="sm"
          >
            Kick
          </Button>
          <Button
            @click="openAction(member, 'ban')"
            variant="danger"
            size="sm"
          >
            Ban
          </Button>
        </div>
      </div>
    </div>

    <div v-else class="text-center py-12 text-discord-text-secondary">
      <div class="text-4xl mb-4">👥</div>
      <p>Tidak ada member ditemukan</p>
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="flex items-center justify-center gap-2 mt-4">
      <Button
        @click="currentPage--"
        :disabled="currentPage === 0"
        variant="secondary"
      >
        Previous
      </Button>
      <span class="text-discord-text-secondary">
        Halaman {{ currentPage + 1 }} dari {{ totalPages }}
      </span>
      <Button
        @click="currentPage++"
        :disabled="currentPage >= totalPages - 1"
        variant="secondary"
      >
        Next
      </Button>
    </div>

    <!-- Action Modal -->
    <div
      v-if="showModal && actionConfig"
      class="fixed inset-0 bg-black/70 flex items-center justify-center z-50"
      @click="closeModal"
    >
      <div class="bg-discord-bg-secondary rounded-lg p-6 max-w-md w-full mx-4" @click.stop>
        <h3 class="text-lg font-bold text-white mb-2">{{ actionConfig.title }}</h3>

        <div v-if="selectedUser" class="mb-4">
          <p class="text-discord-text-secondary mb-2">{{ actionConfig.description }}</p>
          <div class="flex items-center gap-3 p-3 bg-discord-bg-tertiary rounded-lg">
            <div class="w-10 h-10 rounded-full overflow-hidden bg-discord-blurple flex items-center justify-center flex-shrink-0">
              <img
                v-if="selectedUser.avatar && !avatarErrors.has(selectedUser.user_id)"
                :src="getAvatarUrl(selectedUser.avatar)"
                class="w-10 h-10 rounded-full object-cover"
                @error="handleAvatarError(selectedUser.user_id)"
              />
              <span v-else class="text-white font-bold">
                {{ selectedUser.display_name?.charAt(0)?.toUpperCase() || '?' }}
              </span>
            </div>
            <div>
              <div class="font-medium text-white">{{ selectedUser.display_name }}</div>
              <div class="text-sm text-discord-text-secondary">@{{ selectedUser.username }}</div>
            </div>
          </div>
        </div>

        <!-- Duration input -->
        <div v-if="actionConfig.showDuration" class="mb-4">
          <Select
            v-model.number="durationMinutes"
            label="Durasi"
            :options="durationOptions"
          />
        </div>

        <!-- Reason input -->
        <div v-if="actionConfig.showReason" class="mb-4">
          <Input
            v-model="reason"
            label="Alasan (opsional)"
            placeholder="Masukkan alasan..."
          />
        </div>

        <div class="flex justify-end gap-3">
          <Button @click="closeModal" variant="secondary">
            Batal
          </Button>
          <Button @click="executeAction">
            {{ actionConfig.confirmText }}
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.btn-sm {
  padding: 0.375rem 0.75rem;
  font-size: 0.75rem;
}
</style>
