<script setup>
import { onMounted, computed, watch, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'
import { useGuildStore } from '@/stores/guild'
import Card from '@/components/ui/Card.vue'
import Toggle from '@/components/ui/Toggle.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Button from '@/components/ui/Button.vue'
import RoleSelector from '@/components/ui/RoleSelector.vue'

const route = useRoute()
const settingsStore = useSettingsStore()
const guildStore = useGuildStore()

const guildId = computed(() => route.params.guildId)
const newRoleLevel = ref('')
const newRoleId = ref('')
const newRoleStack = ref(false)
const editingRoleId = ref(null) // Track which role ID is being edited
const editLevel = ref('')
const editRoleId = ref('')
const editStack = ref(false)

// Leaderboard edit state
const editingUserId = ref(null)
const editUserLevel = ref('')
const editUserXp = ref('')
const originalUserLevel = ref('')
const originalUserXp = ref('')
const editingEntry = ref(null) // Store the entry being edited

// Leaderboard loading state
const leaderboardLoading = ref(false)

// Leaderboard search and pagination
const leaderboardSearch = ref('')
const leaderboardPage = ref(0)
const leaderboardPerPage = ref(25)

// Sort state
const leaderboardSortColumn = ref('total_xp') // default sort by total_xp
const leaderboardSortDirection = ref('desc') // default descending

const leaderboardPerPageOptions = [
  { value: 10, label: '10 / hal' },
  { value: 25, label: '25 / hal' },
  { value: 50, label: '50 / hal' },
  { value: 100, label: '100 / hal' }
]

// Filter leaderboard by search
const filteredLeaderboard = computed(() => {
  if (!leaderboardSearch.value) return settingsStore.leaderboard
  const query = leaderboardSearch.value.toLowerCase()
  return settingsStore.leaderboard.filter(entry =>
    entry.username?.toLowerCase().includes(query) ||
    entry.display_name?.toLowerCase().includes(query)
  )
})

// Leaderboard sorted by Total XP (for rank calculation - always descending)
const xpSortedLeaderboard = computed(() => {
  const result = [...filteredLeaderboard.value]
  result.sort((a, b) => (b.total_xp || 0) - (a.total_xp || 0))
  return result
})

// Sorted leaderboard (for display - based on current sort column)
const sortedLeaderboard = computed(() => {
  const result = [...filteredLeaderboard.value]
  const column = leaderboardSortColumn.value
  const direction = leaderboardSortDirection.value === 'asc' ? 1 : -1

  result.sort((a, b) => {
    let aVal = a[column]
    let bVal = b[column]

    // Handle string comparison
    if (column === 'username' || column === 'display_name') {
      aVal = (aVal || '').toLowerCase()
      bVal = (bVal || '').toLowerCase()
    }

    if (aVal < bVal) return -1 * direction
    if (aVal > bVal) return 1 * direction
    return 0
  })

  return result
})

// Paginated leaderboard
const leaderboardTotalPages = computed(() => Math.ceil(sortedLeaderboard.value.length / leaderboardPerPage.value))
const paginatedLeaderboard = computed(() => {
  const start = leaderboardPage.value * leaderboardPerPage.value
  const end = start + leaderboardPerPage.value
  return sortedLeaderboard.value.slice(start, end).map((entry, index) => ({
    ...entry,
    displayRank: start + index + 1 // Add display rank for pagination view
  }))
})

// Get actual XP-based rank of entry (always based on Total XP, not current sort)
function getEntryRank(entry) {
  return xpSortedLeaderboard.value.findIndex(e => e.user_id === entry.user_id) + 1
}

// Sort function
function toggleSort(column) {
  if (leaderboardSortColumn.value === column) {
    // Toggle direction if clicking same column
    leaderboardSortDirection.value = leaderboardSortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    // New column - ascending for name, descending for others
    leaderboardSortColumn.value = column
    leaderboardSortDirection.value = column === 'display_name' ? 'asc' : 'desc'
  }
}

// Role options for dropdown
const roleOptions = computed(() => guildStore.getRoleOptions(guildId.value))

// Channel options for dropdown
const channelOptions = computed(() => guildStore.getChannelOptions(guildId.value))

// Reactive roles by ID map (auto-updates when roles change)
const rolesMap = computed(() => {
  const roles = guildStore.roles[guildId.value] || []
  const map = new Map()
  for (const role of roles) {
    map.set(String(role.id), role)
  }
  return map
})

// Get role by ID (now reactive)
function getRoleById(roleId) {
  return rolesMap.value.get(String(roleId))
}

// Get role display with color
function getRoleDisplay(role) {
  const roleData = getRoleById(role.role_id)
  if (roleData) {
    return {
      name: roleData.name,
      color: roleData.color
    }
  }
  return {
    name: `Unknown Role (${role.role_id})`,
    color: null
  }
}

// Check if color is light (for text contrast)
function isColorLight(color) {
  if (!color) return false
  const r = (color >> 16) & 0xff
  const g = (color >> 8) & 0xff
  const b = color & 0xff
  const brightness = (r * 299 + g * 587 + b * 114) / 1000
  return brightness > 128
}

// Store original settings for change detection
const originalSettings = ref('')

// Check if there are unsaved changes
const hasUnsavedChanges = computed(() => {
  // Check settings changes
  let settingsChanged = false
  if (originalSettings.value) {
    const currentSettings = JSON.stringify(settingsStore.levelingSettings)
    settingsChanged = currentSettings !== originalSettings.value
  }

  // Check leaderboard edit changes
  let leaderboardChanged = false
  if (editingUserId.value && originalUserLevel.value !== '' && originalUserXp.value !== '') {
    leaderboardChanged =
      editUserLevel.value !== originalUserLevel.value ||
      editUserXp.value !== originalUserXp.value
  }

  return settingsChanged || leaderboardChanged
})

// Save message based on what changed
const saveMessage = computed(() => {
  const settingsChanged = originalSettings.value &&
    JSON.stringify(settingsStore.levelingSettings) !== originalSettings.value

  const leaderboardChanged = editingUserId.value &&
    originalUserLevel.value !== '' &&
    (editUserLevel.value !== originalUserLevel.value || editUserXp.value !== originalUserXp.value)

  if (settingsChanged && leaderboardChanged) {
    return 'Perubahan pengaturan & XP user belum disimpan'
  } else if (leaderboardChanged) {
    return 'Perubahan XP user belum disimpan'
  }
  return 'Perubahan pengaturan belum disimpan'
})

// Reset original settings after save
function resetOriginalSettings() {
  originalSettings.value = JSON.stringify(settingsStore.levelingSettings)
}

onMounted(() => {
  loadSettings()
})

watch(guildId, () => {
  originalSettings.value = ''
  loadSettings()
})

// Reset leaderboard page when search or perPage changes
watch([leaderboardSearch, leaderboardPerPage], () => {
  leaderboardPage.value = 0
})

async function loadSettings() {
  leaderboardLoading.value = true
  await Promise.all([
    settingsStore.loadLevelingSettings(guildId.value),
    settingsStore.loadLevelRoles(guildId.value),
    settingsStore.loadExcludedRoles(guildId.value),
    settingsStore.loadLeaderboard(guildId.value, 500), // Load more users
    guildStore.loadRoles(guildId.value),
    guildStore.loadChannels(guildId.value)
  ])
  // Set original settings after loading
  originalSettings.value = JSON.stringify(settingsStore.levelingSettings)
  leaderboardLoading.value = false
}

async function saveSettings() {
  // Save leaderboard user XP first if editing
  if (editingUserId.value && editingEntry.value) {
    if (!editUserLevel.value || isNaN(editUserLevel.value) ||
        editUserXp.value === '' || isNaN(editUserXp.value)) {
      settingsStore.showStatus('Please enter level and XP', 'error')
      return
    }
    await settingsStore.setUserXp(
      guildId.value,
      editingEntry.value.user_id,
      parseInt(editUserLevel.value),
      parseInt(editUserXp.value)
    )
  }

  // Save leveling settings if changed
  const currentSettings = JSON.stringify(settingsStore.levelingSettings)
  if (originalSettings.value && currentSettings !== originalSettings.value) {
    const success = await settingsStore.saveLevelingSettings(guildId.value)
    if (success) {
      resetOriginalSettings()
    }
  }

  // Exit edit mode after saving
  if (editingUserId.value) {
    editingUserId.value = null
    editUserLevel.value = ''
    editUserXp.value = ''
    originalUserLevel.value = ''
    originalUserXp.value = ''
    editingEntry.value = null
  }
}

async function addLevelRole() {
  if (!newRoleLevel.value || !newRoleId.value) {
    settingsStore.showStatus('Please enter level and role', 'error')
    return
  }
  await settingsStore.addLevelRole(
    guildId.value,
    parseInt(newRoleLevel.value),
    newRoleId.value,
    newRoleStack.value
  )
  newRoleLevel.value = ''
  newRoleId.value = ''
  newRoleStack.value = false
}

function startEdit(role) {
  editingRoleId.value = role.id
  editLevel.value = role.level.toString()
  editRoleId.value = role.role_id
  editStack.value = !!role.stack
}

function cancelEdit() {
  editingRoleId.value = null
  editLevel.value = ''
  editRoleId.value = ''
  editStack.value = false
}

async function saveInlineEdit(role) {
  if (!editLevel.value || !editRoleId.value) {
    settingsStore.showStatus('Please enter level and role', 'error')
    return
  }
  await settingsStore.updateLevelRole(
    guildId.value,
    role.level,
    role.role_id,
    parseInt(editLevel.value),
    editRoleId.value,
    editStack.value
  )
  editingRoleId.value = null
}

async function removeLevelRole(role) {
  await settingsStore.removeLevelRole(guildId.value, role.level, role.role_id)
}

// Excluded roles functions
async function toggleExcludedRole(roleId) {
  const isExcluded = settingsStore.excludedRoles.includes(roleId)
  if (isExcluded) {
    await settingsStore.removeExcludedRole(guildId.value, roleId)
  } else {
    await settingsStore.addExcludedRole(guildId.value, roleId)
  }
}

// Leaderboard edit functions
function startUserEdit(entry) {
  editingUserId.value = entry.user_id
  editUserLevel.value = entry.level.toString()
  editUserXp.value = entry.xp.toString()
  originalUserLevel.value = entry.level.toString()
  originalUserXp.value = entry.xp.toString()
  editingEntry.value = entry
}

function cancelUserEdit() {
  editingUserId.value = null
  editUserLevel.value = ''
  editUserXp.value = ''
  originalUserLevel.value = ''
  originalUserXp.value = ''
  editingEntry.value = null
}

async function saveUserEdit(entry) {
  if (!editUserLevel.value || isNaN(editUserLevel.value) ||
      editUserXp.value === '' || isNaN(editUserXp.value)) {
    settingsStore.showStatus('Please enter level and XP', 'error')
    return
  }
  await settingsStore.setUserXp(
    guildId.value,
    entry.user_id,
    parseInt(editUserLevel.value),
    parseInt(editUserXp.value)
  )
  editingUserId.value = null
}

async function resetUser(entry) {
  if (confirm(`Reset XP for user ${entry.username || entry.user_id}?`)) {
    await settingsStore.resetUserXp(guildId.value, entry.user_id)
  }
}

function getRequiredXp(level) {
  // XP needed to reach this level from previous level
  // Level 1 -> 2: 150 XP
  // Level 2 -> 3: 200 XP
  // Formula: 150 + (level - 1) * 50
  if (level <= 1) return 150
  return 150 + (level - 1) * 50
}

function getRequiredXpForNext(level) {
  // XP needed to reach the NEXT level
  // Level 1 needs 150 to reach level 2
  // Level 2 needs 200 to reach level 3
  // Formula: 150 + level * 50
  return 150 + level * 50
}

function getAvatarUrl(entry) {
  if (!entry.avatar_url) {
    return `https://cdn.discordapp.com/embed/avatars/${(entry.user_id || 0) % 5}.png`
  }
  // Remove extension from Discord avatar URL to let CDN auto-detect format (PNG/GIF)
  // This handles GIF avatars for Nitro users
  return entry.avatar_url.replace(/\.(png|jpg|jpeg|webp|gif)$/, '')
}
</script>

<template>
  <div class="space-y-6 pb-24">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 bg-gradient-to-br from-discord-blurple to-indigo-600 rounded-xl flex items-center justify-center shadow-lg">
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
          </svg>
        </div>
        <div>
          <h2 class="text-xl font-bold text-white">Leveling System</h2>
          <p class="text-discord-text-secondary text-sm">Configure XP and level rewards</p>
        </div>
      </div>
    </div>

    <!-- Enable Leveling -->
    <Card>
      <template #title>
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-discord-blurple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
          </svg>
          <span>Enable Leveling</span>
        </div>
      </template>
      <Toggle
        v-model="settingsStore.levelingSettings.enabled"
        label="Enable Leveling"
        description="Allow members to gain XP and level up"
      />
    </Card>

    <!-- XP Settings -->
    <Card>
      <template #title>
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-discord-blurple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
          </svg>
          <span>XP Configuration</span>
        </div>
      </template>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Input
          v-model.number="settingsStore.levelingSettings.xp_per_message"
          type="number"
          label="XP per Message"
          :min="1"
          :max="100"
        />
        <Input
          v-model.number="settingsStore.levelingSettings.cooldown_seconds"
          type="number"
          label="Cooldown (seconds)"
          :min="3"
          :max="3600"
          description="Time between XP gains per user"
        />
        <Input
          v-model.number="settingsStore.levelingSettings.min_message_length"
          type="number"
          label="Min. Karakter"
          :min="0"
          :max="2000"
          description="Minimal karakter untuk dapat XP"
        />
      </div>
    </Card>

    <!-- Level Up Notification Channel -->
    <Card>
      <template #title>
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-discord-blurple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
          </svg>
          <span>Notifikasi Level Up</span>
        </div>
      </template>
      <div class="space-y-4">
        <p class="text-discord-text-secondary text-sm">
          Pilih channel di mana bot akan mengirim notifikasi saat member naik level
        </p>
        <div class="max-w-md">
          <Select
            v-model="settingsStore.levelingSettings.level_up_channel_id"
            label="Level Up Channel"
            placeholder="Pilih channel (opsional)"
            :options="channelOptions"
          />
        </div>
        <p class="text-xs text-discord-text-secondary">
          * Jika tidak dipilih, notifikasi level up akan dikirim di channel tempat message terkirim.
        </p>
      </div>
    </Card>

    <!-- Excluded Roles -->
    <Card>
      <template #title>
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-discord-blurple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"/>
          </svg>
          <span>Pengecualian Role</span>
        </div>
      </template>
      <div class="space-y-4">
        <p class="text-discord-text-secondary text-sm">
          Role di bawah ini tidak akan mendapatkan XP dan tidak muncul di leaderboard.
        </p>

        <RoleSelector
          :roles="roleOptions"
          :selected-ids="settingsStore.excludedRoles"
          @toggle="toggleExcludedRole"
        />

        <div v-if="settingsStore.excludedRoles.length === 0" class="text-center py-6 text-discord-text-tertiary text-sm italic">
          Tidak ada role yang dikecualikan
        </div>
      </div>
    </Card>

    <!-- Level Roles -->
    <Card>
      <template #title>
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-discord-yellow" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"/>
          </svg>
          <div class="flex items-center gap-2">
            <h3 class="text-lg font-semibold">Level Roles</h3>
            <div class="tooltip-wrapper group relative">
              <span class="tooltip-icon text-discord-text-tertiary cursor-help border border-discord-text-tertiary rounded-full w-4 h-4 flex items-center justify-center text-xs">?</span>
              <div class="tooltip-text absolute bottom-full left-1/2 -translate-x-1/2 mb-2 p-3 bg-black text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity w-64 text-center pointer-events-none z-10 shadow-lg">
                Role will be automatically assigned when member reaches the level.
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- Add Role Form -->
      <div class="mb-6 p-4 bg-discord-bg-tertiary rounded-lg border border-discord-bg-secondary">
        <h4 class="text-sm font-semibold text-discord-text-secondary uppercase mb-3">Add New Level Role</h4>
        <div class="flex flex-col md:flex-row gap-4 md:items-end">
          <div class="w-full md:w-24">
            <Input v-model="newRoleLevel" type="number" label="Level" placeholder="10" />
          </div>
          <div class="flex-1">
            <Select
              v-model="newRoleId"
              label="Role Reward"
              placeholder="Select a role..."
              :options="roleOptions"
            />
          </div>
          <div class="flex items-end gap-2 shrink-0">
             <div class="flex flex-col gap-2">
              <div class="flex items-center gap-1">
                <label class="text-sm font-medium text-discord-text-secondary">Stack</label>
                <div class="group relative">
                  <span class="text-discord-text-tertiary cursor-help border border-discord-text-tertiary rounded-full w-3.5 h-3.5 flex items-center justify-center text-[10px]">?</span>
                  <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 p-2 bg-black text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity w-48 text-center pointer-events-none z-10 shadow-lg">
                    Jika diaktifkan, user akan mempertahankan role sebelumnya saat naik level.
                  </div>
                </div>
              </div>
              <button
                @click="newRoleStack = !newRoleStack"
                class="h-[42px] px-4 rounded border transition-colors flex items-center gap-2 whitespace-nowrap"
                :class="newRoleStack ? 'bg-discord-green/20 border-discord-green text-discord-green' : 'bg-discord-bg-secondary border-discord-bg-primary text-discord-text-secondary hover:border-discord-text-secondary'"
                type="button"
                title="If stacked, user keeps previous roles"
              >
                 <svg v-if="newRoleStack" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                 <span>{{ newRoleStack ? 'Stacked' : 'No Stack' }}</span>
              </button>
            </div>
            <Button @click="addLevelRole" class="h-[42px] px-6">
              Add
            </Button>
          </div>
        </div>
      </div>

      <div v-if="settingsStore.levelRoles.length > 0">
        <!-- Display Mode - List View -->
        <div v-if="!editingRoleId" class="flex flex-col gap-2">
          <div
            v-for="role in settingsStore.levelRoles"
            :key="role.id"
            class="flex items-center justify-between p-3 bg-discord-bg-secondary rounded-lg hover:bg-discord-bg-tertiary transition-colors border border-transparent hover:border-discord-blurple group"
          >
            <div class="flex items-center gap-4">
              <!-- Level Badge -->
              <div class="flex flex-col items-center justify-center w-12 h-12 bg-discord-bg-tertiary rounded-lg border border-discord-bg-primary">
                <span class="text-[10px] text-discord-text-secondary uppercase">Level</span>
                <span class="text-lg font-bold text-discord-blurple">{{ role.level }}</span>
              </div>
              
              <!-- Role Info -->
              <div>
                <div class="flex items-center gap-2">
                  <span
                    class="px-2 py-0.5 rounded text-sm font-medium"
                    :style="{
                       backgroundColor: getRoleDisplay(role).color ? '#' + getRoleDisplay(role).color.toString(16).padStart(6, '0') + '20' : '#5865f220',
                       color: getRoleDisplay(role).color ? '#' + getRoleDisplay(role).color.toString(16).padStart(6, '0') : '#5865f2'
                    }"
                  >
                    @{{ getRoleDisplay(role).name }}
                  </span>
                  <span v-if="role.stack" class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-discord-green/20 text-discord-green border border-discord-green/30 uppercase">Stack</span>
                </div>
              </div>
            </div>

            <!-- Actions -->
            <div class="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
              <button @click="startEdit(role)" class="p-2 text-discord-text-secondary hover:text-white hover:bg-discord-bg-primary rounded transition-colors" title="Edit">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/></svg>
              </button>
              <button @click="removeLevelRole(role)" class="p-2 text-discord-text-secondary hover:text-discord-red hover:bg-discord-bg-primary rounded transition-colors" title="Delete">
                 <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
              </button>
            </div>
          </div>
        </div>

        <!-- Edit Mode - Single Row -->
        <div v-else class="bg-discord-bg-tertiary px-4 py-3 rounded-lg">
          <div
            v-for="role in settingsStore.levelRoles"
            :key="role.id"
            v-show="editingRoleId === role.id"
          >
            <div class="flex items-center gap-2 flex-1 mb-2">
              <Input v-model="editLevel" type="number" label="Level" class="w-24" :min="1" />
              <Select v-model="editRoleId" label="Role" placeholder="Select role" :options="roleOptions" class="flex-1" />
              <div class="flex items-center gap-2 pb-2">
                <label class="text-sm text-discord-text-secondary">Stack</label>
                <button
                  @click="editStack = !editStack"
                  class="toggle-switch w-10"
                  :class="{ active: editStack }"
                  type="button"
                >
                  <input type="checkbox" :checked="editStack" class="hidden" />
                </button>
              </div>
            </div>
            <div class="flex gap-2">
              <Button variant="secondary" @click="cancelEdit">Cancel</Button>
              <Button @click="saveInlineEdit(role)">Save</Button>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="text-center py-8 text-discord-text-secondary">
        <p>No level roles configured yet</p>
      </div>
    </Card>

    <!-- Leaderboard -->
    <Card>
      <template #title>
        <div class="flex items-center gap-2">
           <svg class="w-5 h-5 text-discord-yellow" fill="currentColor" viewBox="0 0 24 24">
            <path d="M5 3h14c.55 0 1 .45 1 1v2c0 2.21-1.79 4-4 4h-.24c-.45 1.41-1.6 2.54-3.01 2.91V16h2.5c.83 0 1.5.67 1.5 1.5v.5H7.25v-.5c0-.83.67-1.5 1.5-1.5h2.5v-3.09c-1.41-.37-2.56-1.5-3.01-2.91H8c-2.21 0-4-1.79-4-4V4c0-.55.45-1 1-1zm1 3V5h2v1.5C8 7.33 7.33 8 6.5 8H6V6zm12 0V5h-2v1.5c0 .83.67 1.5 1.5 1.5h.5V6z"/>
          </svg>
           <span>Leaderboard</span>
        </div>
      </template>

      <!-- Loading State -->
      <div v-if="leaderboardLoading" class="flex flex-col items-center justify-center py-16 gap-4">
        <div class="w-10 h-10 border-3 border-discord-blurple border-t-transparent rounded-full animate-spin"></div>
        <span class="text-discord-text-secondary">Loading leaderboard...</span>
      </div>

      <!-- Empty State -->
      <div v-else-if="filteredLeaderboard.length === 0" class="text-center py-16">
        <svg class="w-16 h-16 mx-auto text-discord-text-tertiary mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
        </svg>
        <p class="text-discord-text-secondary">{{ leaderboardSearch ? 'No users found matching your search' : 'No users on the leaderboard yet' }}</p>
      </div>

      <!-- Podium for Top 3 -->
      <div v-if="filteredLeaderboard.length >= 3 && !leaderboardSearch" class="mb-8 overflow-x-auto">
        <div class="flex items-end justify-center gap-2 sm:gap-4 min-w-[300px] scale-[0.85] sm:scale-100 origin-center">
          <!-- 2nd Place -->
          <div class="flex flex-col items-center">
            <div class="relative mb-2">
              <img
                :src="getAvatarUrl(filteredLeaderboard[1])"
                class="w-16 h-16 rounded-full object-cover ring-4 ring-[#C0C0C0] shadow-lg"
                onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'"
              />
              <div class="absolute -bottom-1 -right-1 w-6 h-6 bg-[#C0C0C0] rounded-full flex items-center justify-center text-black font-bold text-sm shadow">2</div>
            </div>
            <div class="text-center">
              <div class="text-white font-semibold text-sm truncate max-w-[100px]">{{ filteredLeaderboard[1]?.display_name || 'Unknown' }}</div>
              <div class="text-discord-text-tertiary text-xs">Lv. {{ filteredLeaderboard[1]?.level }}</div>
            </div>
            <div class="w-24 h-20 bg-gradient-to-t from-[#C0C0C0]/30 to-[#C0C0C0]/10 rounded-t-lg mt-2 flex items-end justify-center pb-2">
              <span class="text-[#C0C0C0] font-bold text-2xl">2</span>
            </div>
          </div>

          <!-- 1st Place -->
          <div class="flex flex-col items-center -mt-4">
            <div class="relative mb-2">
              <svg class="w-8 h-8 text-[#FFD700] absolute -top-6 left-1/2 -translate-x-1/2" fill="currentColor" viewBox="0 0 24 24">
                <path d="M5 16L3 5l5.5 5L12 4l3.5 6L21 5l-2 11H5zm14 3c0 .6-.4 1-1 1H6c-.6 0-1-.4-1-1v-1h14v1z"/>
              </svg>
              <img
                :src="getAvatarUrl(filteredLeaderboard[0])"
                class="w-20 h-20 rounded-full object-cover ring-4 ring-[#FFD700] shadow-xl"
                onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'"
              />
              <div class="absolute -bottom-1 -right-1 w-7 h-7 bg-[#FFD700] rounded-full flex items-center justify-center text-black font-bold shadow">1</div>
            </div>
            <div class="text-center">
              <div class="text-white font-semibold truncate max-w-[120px]">{{ filteredLeaderboard[0]?.display_name || 'Unknown' }}</div>
              <div class="text-discord-text-tertiary text-xs">Lv. {{ filteredLeaderboard[0]?.level }}</div>
            </div>
            <div class="w-28 h-28 bg-gradient-to-t from-[#FFD700]/30 to-[#FFD700]/10 rounded-t-lg mt-2 flex items-end justify-center pb-2">
              <span class="text-[#FFD700] font-bold text-3xl">1</span>
            </div>
          </div>

          <!-- 3rd Place -->
          <div class="flex flex-col items-center">
            <div class="relative mb-2">
              <img
                :src="getAvatarUrl(filteredLeaderboard[2])"
                class="w-16 h-16 rounded-full object-cover ring-4 ring-[#CD7F32] shadow-lg"
                onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'"
              />
              <div class="absolute -bottom-1 -right-1 w-6 h-6 bg-[#CD7F32] rounded-full flex items-center justify-center text-black font-bold text-sm shadow">3</div>
            </div>
            <div class="text-center">
              <div class="text-white font-semibold text-sm truncate max-w-[100px]">{{ filteredLeaderboard[2]?.display_name || 'Unknown' }}</div>
              <div class="text-discord-text-tertiary text-xs">Lv. {{ filteredLeaderboard[2]?.level }}</div>
            </div>
            <div class="w-24 h-16 bg-gradient-to-t from-[#CD7F32]/30 to-[#CD7F32]/10 rounded-t-lg mt-2 flex items-end justify-center pb-2">
              <span class="text-[#CD7F32] font-bold text-2xl">3</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Search & Pagination Controls -->
      <div class="flex flex-col sm:flex-row gap-4 mb-6">
        <div class="flex-1">
          <Input
            v-model="leaderboardSearch"
            placeholder="Search by username or display name..."
          />
        </div>
        <div class="w-32">
          <Select
            v-model.number="leaderboardPerPage"
            :options="leaderboardPerPageOptions"
          />
        </div>
      </div>

      <!-- Leaderboard List -->
      <div v-if="filteredLeaderboard.length > 0" class="space-y-3">
        <div
          v-for="entry in paginatedLeaderboard"
          :key="entry.user_id"
          class="relative p-4 rounded-xl transition-all duration-200 group"
          :class="[
            getEntryRank(entry) === 1 ? 'bg-gradient-to-r from-[#FFD700]/10 to-transparent border border-[#FFD700]/30' :
            getEntryRank(entry) === 2 ? 'bg-gradient-to-r from-[#C0C0C0]/10 to-transparent border border-[#C0C0C0]/30' :
            getEntryRank(entry) === 3 ? 'bg-gradient-to-r from-[#CD7F32]/10 to-transparent border border-[#CD7F32]/30' :
            'bg-discord-bg-secondary hover:bg-discord-bg-tertiary border border-transparent',
            editingUserId === entry.user_id ? 'ring-2 ring-discord-blurple' : ''
          ]"
        >
          <div class="flex items-center gap-4">
            <!-- Rank Badge -->
            <div 
              class="w-10 h-10 flex items-center justify-center rounded-xl font-bold text-lg shrink-0"
              :class="{
                'bg-[#FFD700] text-black shadow-lg shadow-[#FFD700]/30': getEntryRank(entry) === 1,
                'bg-[#C0C0C0] text-black shadow-lg shadow-[#C0C0C0]/30': getEntryRank(entry) === 2,
                'bg-[#CD7F32] text-black shadow-lg shadow-[#CD7F32]/30': getEntryRank(entry) === 3,
                'bg-discord-bg-tertiary text-discord-text-secondary': getEntryRank(entry) > 3
              }"
            >
              <!-- Rank Number -->
              <span class="text-sm">{{ getEntryRank(entry) }}</span>
            </div>

            <!-- Avatar -->
            <div class="relative shrink-0">
              <img
                :src="getAvatarUrl(entry)"
                class="w-12 h-12 rounded-full object-cover ring-2"
                :class="{
                  'ring-[#FFD700]': getEntryRank(entry) === 1,
                  'ring-[#C0C0C0]': getEntryRank(entry) === 2,
                  'ring-[#CD7F32]': getEntryRank(entry) === 3,
                  'ring-discord-bg-tertiary': getEntryRank(entry) > 3
                }"
                onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'"
                alt="Avatar"
              />
            </div>

            <!-- User Info & XP Progress -->
            <div class="flex-1 min-w-0">
              <!-- Edit Mode -->
              <template v-if="editingUserId === entry.user_id">
                <div class="flex items-center gap-4">
                  <div>
                    <div class="text-white font-semibold">{{ entry.display_name || 'Unknown User' }}</div>
                    <div class="text-discord-text-tertiary text-xs">@{{ entry.username || 'unknown' }}</div>
                  </div>
                  <div class="flex items-center gap-2 ml-auto">
                    <div class="flex flex-col">
                      <label class="text-[10px] text-discord-text-tertiary uppercase">Level</label>
                      <input
                        v-model.number="editUserLevel"
                        type="number"
                        class="w-16 bg-discord-bg-primary border border-discord-bg-tertiary rounded px-2 py-1 text-white text-sm focus:ring-1 focus:ring-discord-blurple"
                        :min="1"
                      />
                    </div>
                    <div class="flex flex-col">
                      <label class="text-[10px] text-discord-text-tertiary uppercase">XP</label>
                      <input
                        v-model.number="editUserXp"
                        type="number"
                        class="w-20 bg-discord-bg-primary border border-discord-bg-tertiary rounded px-2 py-1 text-white text-sm focus:ring-1 focus:ring-discord-blurple"
                        :min="0"
                      />
                    </div>
                    <button @click="cancelUserEdit" class="p-2 text-discord-text-secondary hover:text-white hover:bg-discord-bg-primary rounded-lg transition-colors" title="Cancel">
                      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                    </button>
                  </div>
                </div>
              </template>

              <!-- Display Mode -->
              <template v-else>
                <div class="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
                  <div class="min-w-0">
                    <div class="text-white font-semibold truncate">{{ entry.display_name || 'Unknown User' }}</div>
                    <div class="text-discord-text-tertiary text-xs">@{{ entry.username || 'unknown' }}</div>
                  </div>
                  
                  <div class="flex items-center gap-4 sm:ml-auto">
                    <!-- Level Badge -->
                    <div class="flex flex-col items-center px-3 py-1 bg-discord-bg-tertiary rounded-lg">
                      <span class="text-[10px] text-discord-text-tertiary uppercase">Level</span>
                      <span class="text-lg font-bold text-discord-blurple">{{ entry.level }}</span>
                    </div>

                    <!-- XP Progress -->
                    <div class="flex-1 sm:w-40">
                      <div class="flex justify-between text-xs mb-1">
                        <span class="text-discord-text-secondary">{{ entry.xp }} / {{ getRequiredXpForNext(entry.level) }} XP</span>
                      </div>
                      <div class="h-2 bg-discord-bg-primary rounded-full overflow-hidden">
                        <div 
                          class="h-full rounded-full transition-all duration-500"
                          :class="{
                            'bg-gradient-to-r from-[#FFD700] to-[#FFA500]': getEntryRank(entry) === 1,
                            'bg-gradient-to-r from-[#C0C0C0] to-[#A0A0A0]': getEntryRank(entry) === 2,
                            'bg-gradient-to-r from-[#CD7F32] to-[#A0522D]': getEntryRank(entry) === 3,
                            'bg-gradient-to-r from-discord-blurple to-discord-blurple-dark': getEntryRank(entry) > 3
                          }"
                          :style="{ width: `${Math.min((entry.xp / getRequiredXpForNext(entry.level)) * 100, 100)}%` }"
                        ></div>
                      </div>
                    </div>

                    <!-- Total XP -->
                    <div class="text-right hidden sm:block">
                      <div class="text-[10px] text-discord-text-tertiary uppercase">Total</div>
                      <div class="text-sm font-semibold text-discord-text-primary">{{ entry.total_xp.toLocaleString() }} XP</div>
                    </div>
                  </div>
                </div>
              </template>
            </div>

            <!-- Actions (Display Mode Only) -->
            <div v-if="editingUserId !== entry.user_id" class="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
              <button
                @click="startUserEdit(entry)"
                class="p-2 text-discord-text-secondary hover:text-discord-blurple hover:bg-discord-bg-primary rounded-lg transition-colors"
                title="Edit"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/></svg>
              </button>
              <button
                @click="resetUser(entry)"
                class="p-2 text-discord-text-secondary hover:text-discord-red hover:bg-discord-bg-primary rounded-lg transition-colors"
                title="Reset"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Pagination -->
      <div v-if="leaderboardTotalPages > 1" class="flex items-center justify-center gap-3 mt-6 pt-6 border-t border-discord-bg-tertiary">
        <button
          @click="leaderboardPage--"
          :disabled="leaderboardPage === 0"
          class="px-4 py-2 bg-discord-bg-secondary hover:bg-discord-bg-tertiary disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-sm text-white flex items-center gap-2 transition-colors"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
          Previous
        </button>
        <div class="flex items-center gap-1">
          <span class="px-3 py-1 bg-discord-blurple rounded-lg text-sm font-semibold text-white">{{ leaderboardPage + 1 }}</span>
          <span class="text-discord-text-secondary text-sm">of {{ leaderboardTotalPages }}</span>
        </div>
        <button
          @click="leaderboardPage++"
          :disabled="leaderboardPage >= leaderboardTotalPages - 1"
          class="px-4 py-2 bg-discord-bg-secondary hover:bg-discord-bg-tertiary disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-sm text-white flex items-center gap-2 transition-colors"
        >
          Next
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
        </button>
      </div>
    </Card>

    <!-- Floating Save Button -->
    <Transition
      enter-active-class="transition-all duration-300 ease-out"
      enter-from-class="translate-y-20 opacity-0"
      enter-to-class="translate-y-0 opacity-100"
      leave-active-class="transition-all duration-300 ease-in"
      leave-from-class="translate-y-0 opacity-100"
      leave-to-class="translate-y-20 opacity-0"
    >
      <div
        v-if="hasUnsavedChanges"
        class="fixed bottom-6 right-6 z-50 flex items-center gap-4 bg-discord-bg-primary px-6 py-3 rounded-lg shadow-2xl border border-discord-bg-tertiary"
      >
        <span class="text-sm text-discord-text-secondary">{{ saveMessage }}</span>
        <Button @click="saveSettings">Simpan Perubahan</Button>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.tooltip-wrapper {
  position: relative;
  display: inline-block;
}

.tooltip-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.25rem;
  height: 1.25rem;
  background: #5865f2;
  color: white;
  border-radius: 50%;
  font-size: 0.75rem;
  font-weight: bold;
  cursor: help;
  transition: background 0.15s ease;
}

.tooltip-icon:hover {
  background: #4752c4;
}

.tooltip-text {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%) translateY(-0.5rem);
  width: 16rem;
  padding: 0.75rem;
  background: #111214;
  border: 1px solid #1e1f22;
  border-radius: 0.5rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
  color: #dbdee1;
  font-size: 0.875rem;
  line-height: 1.4;
  opacity: 0;
  visibility: hidden;
  transition: all 0.15s ease;
  z-index: 100;
  pointer-events: none;
}

.tooltip-wrapper:hover .tooltip-text {
  opacity: 1;
  visibility: visible;
  transform: translateX(-50%) translateY(-0.25rem);
}
</style>
