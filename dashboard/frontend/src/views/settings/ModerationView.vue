<script setup>
import { onMounted, computed, watch, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'
import { useGuildStore } from '@/stores/guild'
import Card from '@/components/ui/Card.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Button from '@/components/ui/Button.vue'
import RoleSelector from '@/components/ui/RoleSelector.vue'
import MembersList from '@/components/moderation/MembersList.vue'
import ModerationLogs from '@/components/moderation/ModerationLogs.vue'

const route = useRoute()
const settingsStore = useSettingsStore()
const guildStore = useGuildStore()

const guildId = computed(() => route.params.guildId)

// Channel options for dropdown
const channelOptions = computed(() => guildStore.getChannelOptions(guildId.value))

// Role options for dropdown
const roleOptions = computed(() => guildStore.getRoleOptions(guildId.value))

// Store original settings for change detection
const originalSettings = ref('')

// Active tab for member/logs section
const activeTab = ref('members')

// Check if there are unsaved changes (only moderation_log_channel_id)
const hasUnsavedChanges = computed(() => {
  if (!originalSettings.value) return false
  const currentLogChannel = settingsStore.guildSettings.moderation_log_channel_id
  const originalParsed = JSON.parse(originalSettings.value)
  const originalLogChannel = originalParsed.moderation_log_channel_id
  return currentLogChannel !== originalLogChannel
})

// Reset original settings after save
function resetOriginalSettings() {
  originalSettings.value = JSON.stringify(settingsStore.guildSettings)
}

onMounted(() => {
  loadSettings()
})

watch(guildId, () => {
  originalSettings.value = ''
  loadSettings()
})

async function loadSettings() {
  await Promise.all([
    settingsStore.loadGuildSettings(guildId.value),
    settingsStore.loadModerationData(guildId.value),
    guildStore.loadChannels(guildId.value),
    guildStore.loadRoles(guildId.value)
  ])
  // Set original settings after loading
  originalSettings.value = JSON.stringify(settingsStore.guildSettings)
}

// Toggle moderation role
function toggleModerationRole(roleId) {
  const index = settingsStore.moderationRoles.findIndex(id => String(id) === String(roleId))
  if (index > -1) {
    settingsStore.removeModerationRole(guildId.value, roleId)
  } else {
    settingsStore.addModerationRole(guildId.value, roleId)
  }
}

async function saveSettings() {
  const success = await settingsStore.saveGuildSettings(guildId.value)
  if (success) {
    resetOriginalSettings()
  }
}
</script>

<template>
  <div class="space-y-6 pb-24">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 bg-gradient-to-br from-discord-red to-red-600 rounded-xl flex items-center justify-center shadow-lg">
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
          </svg>
        </div>
        <div>
          <h2 class="text-xl font-bold text-white">Moderation Settings</h2>
          <p class="text-discord-text-secondary text-sm">Configure moderation tools and logging</p>
        </div>
      </div>
    </div>

    <!-- Logging -->
    <Card>
      <template #title>
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-discord-yellow" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
          <span>Moderation Logging</span>
        </div>
      </template>
      <div class="space-y-4">
        <Select
          v-model="settingsStore.guildSettings.moderation_log_channel_id"
          label="Log Channel"
          placeholder="Pilih channel (opsional)"
          :options="channelOptions"
        />
        <p class="text-xs text-discord-text-tertiary">
          Moderation actions will be logged to this channel
        </p>
      </div>
    </Card>

    <!-- Moderation Roles -->
    <Card>
      <template #title>
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-discord-blurple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>
          </svg>
          <span>Moderation Roles</span>
        </div>
      </template>
      <p class="text-discord-text-tertiary text-sm mb-4">
        Role di bawah ini memiliki akses ke command moderation
      </p>

      <RoleSelector
        :roles="roleOptions"
        :selected-ids="settingsStore.moderationRoles"
        @toggle="toggleModerationRole"
      />

      <div v-if="settingsStore.moderationRoles.length === 0" class="text-center py-8 text-discord-text-tertiary">
        <svg class="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
        </svg>
        <p class="font-medium">Tidak ada role moderation yang dipilih</p>
        <p class="text-xs mt-1">Roles dengan Administrator permission memiliki akses default</p>
      </div>
    </Card>

    <!-- Member & Logs Tabs -->
    <Card>
      <template #title>
        <div class="flex items-center justify-between w-full">
          <div class="flex items-center gap-2">
            <svg v-if="activeTab === 'members'" class="w-5 h-5 text-discord-red" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"/>
            </svg>
            <svg v-else class="w-5 h-5 text-discord-yellow" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
            <span>{{ activeTab === 'members' ? 'Member Management' : 'Moderation Logs' }}</span>
          </div>
          <!-- Tab Buttons -->
          <div class="flex bg-discord-bg-tertiary rounded-lg p-1 gap-1">
            <button
              @click="activeTab = 'members'"
              class="px-4 py-1.5 text-sm font-medium rounded-md transition-all duration-200"
              :class="activeTab === 'members' 
                ? 'bg-discord-blurple text-white shadow-sm' 
                : 'text-discord-text-secondary hover:text-white hover:bg-discord-bg-hover'"
            >
              <div class="flex items-center gap-2">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
                </svg>
                Members
              </div>
            </button>
            <button
              @click="activeTab = 'logs'"
              class="px-4 py-1.5 text-sm font-medium rounded-md transition-all duration-200"
              :class="activeTab === 'logs' 
                ? 'bg-discord-blurple text-white shadow-sm' 
                : 'text-discord-text-secondary hover:text-white hover:bg-discord-bg-hover'"
            >
              <div class="flex items-center gap-2">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
                Logs
              </div>
            </button>
          </div>
        </div>
      </template>

      <!-- Tab Content -->
      <div class="mt-2">
        <!-- Members Tab -->
        <div v-show="activeTab === 'members'">
          <p class="text-discord-text-tertiary text-sm mb-4">
            Kelola member server dengan action ban, kick, dan timeout
          </p>
          <MembersList :guild-id="guildId" />
        </div>

        <!-- Logs Tab -->
        <div v-show="activeTab === 'logs'">
          <p class="text-discord-text-tertiary text-sm mb-4">
            Riwayat tindakan moderasi pada server
          </p>
          <ModerationLogs :guild-id="guildId" />
        </div>
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
        <span class="text-sm text-discord-text-secondary">You have unsaved changes</span>
        <Button @click="saveSettings">Save Changes</Button>
      </div>
    </Transition>
  </div>
</template>
