<script setup>
import { onMounted, computed, watch, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'
import { useGuildStore } from '@/stores/guild'
import { useLocaleStore } from '@/stores/locale'
import Card from '@/components/ui/Card.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Button from '@/components/ui/Button.vue'
import Toggle from '@/components/ui/Toggle.vue'

const route = useRoute()
const settingsStore = useSettingsStore()
const guildStore = useGuildStore()
const localeStore = useLocaleStore()

const guildId = computed(() => route.params.guildId)

// Store original settings for change detection
const originalSettings = ref('')

// Check if there are unsaved changes
const hasUnsavedChanges = computed(() => {
  if (!originalSettings.value) return false
  return JSON.stringify(settingsStore.guildSettings) !== originalSettings.value
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
    guildStore.loadChannels(guildId.value),
    guildStore.loadRoles(guildId.value)
  ])
  originalSettings.value = JSON.stringify(settingsStore.guildSettings)
}

async function saveSettings() {
  const success = await settingsStore.saveGuildSettings(guildId.value)
  if (success) {
    resetOriginalSettings()
  }
}

// Handle language change
function onLanguageChange(locale) {
  localeStore.setLocale(locale)
}

// Translation helper
const t = (key) => localeStore.t(key)
</script>

<template>
  <div class="space-y-6 pb-24">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 bg-gradient-to-br from-gray-500 to-gray-700 rounded-xl flex items-center justify-center shadow-lg">
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"/>
          </svg>
        </div>
        <div>
          <h2 class="text-xl font-bold text-white">{{ t('settings.title') }}</h2>
          <p class="text-discord-text-secondary text-sm">{{ t('settings.subtitle') }}</p>
        </div>
      </div>
    </div>

    <!-- Preferences -->
    <Card>
      <template #title>
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-discord-blurple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
          </svg>
          <span>{{ t('settings.preferences') }}</span>
        </div>
      </template>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Dashboard Language -->
        <Select
          :model-value="localeStore.currentLocale"
          @update:model-value="onLanguageChange"
          :label="t('settings.language')"
          :placeholder="t('settings.languagePlaceholder')"
          :options="localeStore.availableLocales"
        />

        <!-- Bot Prefix -->
        <Input
          v-model="settingsStore.guildSettings.prefix"
          :label="t('settings.prefix')"
          placeholder="!"
        />

        <!-- Delete Command Messages -->
        <div class="flex items-center justify-between p-3 bg-discord-bg-tertiary rounded-lg">
          <div>
            <p class="text-white font-medium">{{ t('settings.deleteMessages') }}</p>
            <p class="text-xs text-discord-text-tertiary">{{ t('settings.deleteMessagesDesc') }}</p>
          </div>
          <Toggle
            v-model="settingsStore.guildSettings.delete_command_messages"
          />
        </div>
      </div>
    </Card>

    <!-- Notifications -->
    <Card>
      <template #title>
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-discord-yellow" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
          </svg>
          <span>{{ t('settings.notifications') }}</span>
        </div>
      </template>

      <div class="space-y-4">
        <!-- DM on Level Up -->
        <div class="flex items-center justify-between p-3 bg-discord-bg-tertiary rounded-lg">
          <div>
            <p class="text-white font-medium">{{ t('settings.dmLevelUp') }}</p>
            <p class="text-xs text-discord-text-tertiary">{{ t('settings.dmLevelUpDesc') }}</p>
          </div>
          <Toggle
            v-model="settingsStore.guildSettings.dm_on_level_up"
          />
        </div>

        <!-- DM on Moderation -->
        <div class="flex items-center justify-between p-3 bg-discord-bg-tertiary rounded-lg">
          <div>
            <p class="text-white font-medium">{{ t('settings.dmModeration') }}</p>
            <p class="text-xs text-discord-text-tertiary">{{ t('settings.dmModerationDesc') }}</p>
          </div>
          <Toggle
            v-model="settingsStore.guildSettings.dm_on_moderation"
          />
        </div>
      </div>
    </Card>

    <!-- Danger Zone -->
    <Card>
      <template #title>
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-discord-red" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
          </svg>
          <span>{{ t('settings.dangerZone') }}</span>
        </div>
      </template>

      <div class="space-y-4">
        <div class="p-4 border border-discord-red/30 rounded-lg bg-discord-red/5">
          <h4 class="text-white font-medium mb-2">{{ t('settings.resetSettings') }}</h4>
          <p class="text-sm text-discord-text-secondary mb-4">
            {{ t('settings.resetSettingsDesc') }}
          </p>
          <Button variant="danger" size="sm">
            {{ t('settings.resetButton') }}
          </Button>
        </div>

        <div class="p-4 border border-discord-red/30 rounded-lg bg-discord-red/5">
          <h4 class="text-white font-medium mb-2">{{ t('settings.clearData') }}</h4>
          <p class="text-sm text-discord-text-secondary mb-4">
            {{ t('settings.clearDataDesc') }}
          </p>
          <Button variant="danger" size="sm">
            {{ t('settings.clearButton') }}
          </Button>
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
        <span class="text-sm text-discord-text-secondary">{{ t('common.unsavedChanges') }}</span>
        <Button @click="saveSettings">{{ t('common.save') }}</Button>
      </div>
    </Transition>
  </div>
</template>
