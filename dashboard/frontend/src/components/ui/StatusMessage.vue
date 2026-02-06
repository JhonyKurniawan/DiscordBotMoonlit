<script setup>
import { useSettingsStore } from '@/stores/settings'

const settingsStore = useSettingsStore()
</script>

<template>
  <Transition
    enter-active-class="transition ease-out duration-200"
    enter-from-class="transform opacity-0 translate-y-4"
    enter-to-class="transform opacity-100 translate-y-0"
    leave-active-class="transition ease-in duration-150"
    leave-from-class="opacity-100 translate-y-0"
    leave-to-class="transform opacity-0 translate-y-4"
  >
    <div
      v-if="settingsStore.statusMessage"
      class="fixed bottom-20 right-6 z-50 px-6 py-3 rounded-lg shadow-2xl border min-w-[200px] max-w-md"
      :class="{
        'bg-discord-green/20 text-discord-green border-discord-green': settingsStore.statusType === 'success',
        'bg-discord-red/20 text-discord-red border-discord-red': settingsStore.statusType === 'error'
      }"
    >
      <div class="flex items-center gap-2">
        <span v-if="settingsStore.statusType === 'success'">✓</span>
        <span v-else>✕</span>
        <span>{{ settingsStore.statusMessage }}</span>
      </div>
    </div>
  </Transition>
</template>
