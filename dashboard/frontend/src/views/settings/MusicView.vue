<script setup>
import { onMounted, computed, watch, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'
import { useGuildStore } from '@/stores/guild'
import Card from '@/components/ui/Card.vue'
import Toggle from '@/components/ui/Toggle.vue'
import Select from '@/components/ui/Select.vue'
import Button from '@/components/ui/Button.vue'

const route = useRoute()
const settingsStore = useSettingsStore()
const guildStore = useGuildStore()

const guildId = computed(() => route.params.guildId)

// Channel options for dropdown
const channelOptions = computed(() => guildStore.getChannelOptions(guildId.value))

// Auto disconnect time options
const disconnectTimeOptions = [
  { value: 60, label: '1 menit' },
  { value: 120, label: '2 menit' },
  { value: 300, label: '5 menit' },
  { value: 600, label: '10 menit' },
  { value: 900, label: '15 menit' },
  { value: 1800, label: '30 menit' },
  { value: 3600, label: '60 menit' }
]

// Store original settings for change detection
const originalSettings = ref('')

// Check if there are unsaved changes (only music-related fields)
const hasUnsavedChanges = computed(() => {
  if (!originalSettings.value) return false
  const musicFields = ['music_auto_delete', 'music_default_volume', 'music_shuffle', 'music_repeat', 'music_channel_id', 'auto_disconnect_time']
  const currentMusicSettings = {}
  const originalMusicSettings = {}

  musicFields.forEach(field => {
    currentMusicSettings[field] = settingsStore.guildSettings[field]
    const originalParsed = JSON.parse(originalSettings.value)
    originalMusicSettings[field] = originalParsed[field]
  })

  return JSON.stringify(currentMusicSettings) !== JSON.stringify(originalMusicSettings)
})

// Reset original settings after save
function resetOriginalSettings() {
  originalSettings.value = JSON.stringify(settingsStore.guildSettings)
}

// Custom Genres Modal
const showAddGenreModal = ref(false)
const newGenreName = ref('')
const newGenreQuery = ref('')
const newGenreEmoji = ref('🎵')

// Delete Confirmation Modal
const showDeleteModal = ref(false)
const genreToDelete = ref(null)

const emojiOptions = [
  '🎵', '🎶', '🎼', '🎹', '🎸', '🎺', '🎻', '🥁', '🎤', '🎧',
  '🔥', '⭐', '✨', '💫', '🌟', '💜', '💙', '💚', '💛', '❤️',
  '🎉', '🎊', '🎈', '🎀', '🌈', '☀️', '🌙', '⚡', '💥', '🔮'
]

function openGenreModal() {
  newGenreName.value = ''
  newGenreQuery.value = ''
  newGenreEmoji.value = '🎵'
  showAddGenreModal.value = true
}

function closeGenreModal() {
  showAddGenreModal.value = false
}

async function addGenre() {
  if (!newGenreName.value.trim() || !newGenreQuery.value.trim()) {
    settingsStore.showStatus('Please fill in all fields', 'error')
    return
  }

  await settingsStore.addUserMusicGenre({
    genre_name: newGenreName.value.trim(),
    search_query: newGenreQuery.value.trim(),
    emoji: newGenreEmoji.value
  })

  closeGenreModal()
}

function openDeleteModal(genreId) {
  genreToDelete.value = genreId
  showDeleteModal.value = true
}

function closeDeleteModal() {
  showDeleteModal.value = false
  genreToDelete.value = null
}

async function confirmDelete() {
  if (genreToDelete.value) {
    await settingsStore.deleteUserMusicGenre(genreToDelete.value)
    closeDeleteModal()
  }
}

onMounted(() => {
  loadSettings()
  loadUserGenres()
})

watch(guildId, () => {
  originalSettings.value = ''
  loadSettings()
})

async function loadSettings() {
  await Promise.all([
    settingsStore.loadGuildSettings(guildId.value),
    guildStore.loadChannels(guildId.value)
  ])
  // Set original settings after loading
  originalSettings.value = JSON.stringify(settingsStore.guildSettings)
}

async function loadUserGenres() {
  await settingsStore.loadUserMusicGenres()
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
        <div class="w-10 h-10 bg-gradient-to-br from-discord-green to-teal-600 rounded-xl flex items-center justify-center shadow-lg">
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"/>
          </svg>
        </div>
        <div>
          <h2 class="text-xl font-bold text-white">Music Settings</h2>
          <p class="text-discord-text-secondary text-sm">Configure music player behavior</p>
        </div>
      </div>
    </div>

    <!-- Auto Delete -->
    <Card>
      <template #title>
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-discord-red" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
          </svg>
          <span>Auto-Delete</span>
        </div>
      </template>
      <Toggle
        v-model="settingsStore.guildSettings.music_auto_delete"
        label="Auto-Delete Messages"
        description="Automatically delete music player messages after playback"
      />
    </Card>

    <!-- Music Channel -->
    <Card>
      <template #title>
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-discord-blurple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14"/>
          </svg>
          <span>Music Channel</span>
        </div>
      </template>
      <p class="text-discord-text-secondary text-sm mb-4">
        Pilih channel di mana bot akan mengirim notifikasi music (now playing, queue info, dll)
      </p>
      <Select
        v-model="settingsStore.guildSettings.music_channel_id"
        label="Music Channel"
        placeholder="Pilih channel (opsional)"
        :options="channelOptions"
      />
      <p class="text-xs text-discord-text-tertiary mt-2">
        Jika tidak dipilih, notifikasi music akan dikirim di channel tempat command dipanggil.
      </p>
    </Card>

    <!-- Auto Disconnect & Volume (Side by Side) -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- Auto Disconnect -->
      <Card>
        <template #title>
          <div class="flex items-center gap-2">
            <svg class="w-5 h-5 text-discord-yellow" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <span>Auto Disconnect</span>
          </div>
        </template>
        <Select
          v-model.number="settingsStore.guildSettings.auto_disconnect_time"
          label="Idle Timeout"
          placeholder="Pilih waktu"
          :options="disconnectTimeOptions"
        />
        <p class="text-xs text-discord-text-tertiary mt-2">
          Bot akan otomatis disconnect setelah tidak ada aktivitas.
        </p>
      </Card>

      <!-- Volume Settings -->
      <Card>
        <template #title>
          <div class="flex items-center gap-2">
            <svg class="w-5 h-5 text-discord-green" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"/>
            </svg>
            <span>Volume</span>
          </div>
        </template>
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <label class="text-sm font-medium text-white">Default Volume</label>
            <span class="text-sm font-medium text-discord-blurple">{{ settingsStore.guildSettings.music_default_volume || 50 }}%</span>
          </div>
          <input
            v-model.number="settingsStore.guildSettings.music_default_volume"
            type="range"
            min="0"
            max="100"
            class="w-full h-2 bg-discord-bg-tertiary rounded-lg appearance-none cursor-pointer accent-discord-blurple"
          />
          <p class="text-xs text-discord-text-tertiary">
            Default volume untuk music player (0-100%)
          </p>
        </div>
      </Card>
    </div>

    <!-- Playback Options -->
    <Card>
      <template #title>
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <span>Playback Options</span>
        </div>
      </template>
      <div class="space-y-4">
        <Toggle
          v-model="settingsStore.guildSettings.music_shuffle"
          label="Shuffle by Default"
          description="Enable shuffle mode when adding songs to queue"
        />
        <Toggle
          v-model="settingsStore.guildSettings.music_repeat"
          label="Repeat by Default"
          description="Enable repeat mode when playing music"
        />
      </div>
    </Card>

    <!-- Custom Genres -->
    <Card>
      <template #title>
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-pink-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
          </svg>
          <span>Custom Genres</span>
        </div>
      </template>
      <p class="text-discord-text-tertiary text-sm mb-4">
        Tambahkan genre musik custom yang akan muncul di command <code class="bg-discord-bg-tertiary px-1.5 py-0.5 rounded text-discord-blurple">!rplay</code> dan <code class="bg-discord-bg-tertiary px-1.5 py-0.5 rounded text-discord-blurple">!uplay</code>.
        Genre ini hanya bisa dilihat dan digunakan oleh Anda.
      </p>

      <!-- Genre Grid with Add Button -->
      <div class="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-2">
        <!-- Genre Cards -->
        <div
          v-for="genre in settingsStore.userMusicGenres"
          :key="genre.id"
          class="relative group bg-gradient-to-br from-discord-bg-secondary to-discord-bg-tertiary rounded-lg p-3 hover:from-discord-bg-hover hover:to-discord-bg-secondary transition-all duration-200 border border-discord-bg-tertiary hover:border-pink-500/30 shadow-sm hover:shadow-md"
        >
          <!-- Delete Button -->
          <button
            @click="openDeleteModal(genre.id)"
            class="absolute top-1 right-1 opacity-0 group-hover:opacity-100 text-discord-text-tertiary hover:text-red-500 transition-all p-1 bg-discord-bg-primary/80 rounded-md hover:bg-discord-bg-primary"
            title="Delete genre"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          <!-- Genre Content -->
          <div class="flex flex-col items-center text-center">
            <div class="w-10 h-10 bg-gradient-to-br from-pink-500/20 to-purple-500/20 rounded-lg flex items-center justify-center mb-1.5">
              <span class="text-xl">{{ genre.emoji }}</span>
            </div>
            <p class="text-white font-medium text-xs truncate w-full">{{ genre.genre_name }}</p>
            <p class="text-[10px] text-discord-text-tertiary truncate w-full">{{ genre.search_query }}</p>
          </div>
        </div>

        <!-- Add Genre Button -->
        <div
          @click="openGenreModal"
          class="bg-discord-bg-tertiary border-2 border-dashed border-discord-bg-hover rounded-lg p-3 hover:border-pink-500 hover:bg-discord-bg-hover transition-all cursor-pointer group flex flex-col items-center justify-center"
        >
          <div class="w-10 h-10 bg-discord-bg-hover rounded-lg flex items-center justify-center mb-1.5 group-hover:bg-pink-500/20 transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-discord-text-secondary group-hover:text-pink-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
          </div>
          <p class="text-discord-text-secondary text-xs font-medium group-hover:text-pink-400 transition-colors">Add</p>
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="settingsStore.userMusicGenres.length === 0" class="flex items-center justify-center py-12 border-2 border-dashed border-discord-bg-tertiary rounded-xl mt-4">
        <div class="text-center">
          <button
            @click="openGenreModal"
            class="text-discord-text-secondary hover:text-pink-400 transition-colors flex flex-col items-center gap-3 group"
          >
            <div class="w-16 h-16 bg-discord-bg-tertiary rounded-2xl flex items-center justify-center group-hover:bg-pink-500/20 transition-colors">
              <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"/>
              </svg>
            </div>
            <span class="text-sm font-medium">Add your first custom genre</span>
          </button>
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

    <!-- Add Genre Modal Overlay -->
    <Transition
      enter-active-class="transition-all duration-300 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition-all duration-200 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="showAddGenreModal"
        class="fixed inset-0 z-[100] flex items-center justify-center p-4"
        @click.self="closeGenreModal"
      >
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm"></div>

        <!-- Modal Content -->
        <div class="relative bg-discord-bg-secondary rounded-xl shadow-2xl border border-discord-bg-tertiary w-full max-w-md">
          <!-- Modal Header -->
          <div class="flex items-center justify-between p-4 border-b border-discord-bg-tertiary">
            <h3 class="text-lg font-bold text-white">Add Custom Genre</h3>
            <button
              @click="closeGenreModal"
              class="text-discord-text-secondary hover:text-white transition-colors p-1"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Modal Body -->
          <div class="p-4 space-y-4">
            <!-- Genre Name -->
            <div>
              <label class="text-sm font-medium text-white block mb-2">Genre Name</label>
              <input
                v-model="newGenreName"
                type="text"
                placeholder="Contoh: Dangdut"
                class="w-full px-3 py-2 bg-discord-bg-tertiary border border-discord-bg-tertiary rounded-lg text-white placeholder-discord-text-secondary focus:outline-none focus:border-discord-blurple"
              />
            </div>

            <!-- Search Query -->
            <div>
              <label class="text-sm font-medium text-white block mb-2">Search Query</label>
              <input
                v-model="newGenreQuery"
                type="text"
                placeholder="lagu dangdut terbaru 2024"
                class="w-full px-3 py-2 bg-discord-bg-tertiary border border-discord-bg-tertiary rounded-lg text-white placeholder-discord-text-secondary focus:outline-none focus:border-discord-blurple"
              />
              <p class="text-xs text-discord-text-secondary mt-1">
                Kata pencarian untuk YouTube Music
              </p>
            </div>

            <!-- Emoji Picker -->
            <div>
              <label class="text-sm font-medium text-white block mb-2">Select Emoji</label>
              <div class="grid grid-cols-10 gap-1">
                <button
                  v-for="emoji in emojiOptions"
                  :key="emoji"
                  @click="newGenreEmoji = emoji"
                  :class="[
                    'w-8 h-8 text-lg rounded transition-all flex items-center justify-center',
                    newGenreEmoji === emoji
                      ? 'bg-discord-blurple text-white ring-2 ring-discord-blurple ring-offset-2 ring-offset-discord-bg-secondary'
                      : 'bg-discord-bg-tertiary text-discord-text-secondary hover:bg-discord-bg-hover'
                  ]"
                >
                  {{ emoji }}
                </button>
              </div>
            </div>

            <!-- Preview -->
            <div class="bg-discord-bg-tertiary rounded-lg p-3">
              <p class="text-xs text-discord-text-secondary mb-1">Preview:</p>
              <div class="flex items-center gap-2">
                <span class="text-2xl">{{ newGenreEmoji }}</span>
                <span class="text-white font-medium">{{ newGenreName || 'Genre Name' }}</span>
              </div>
            </div>
          </div>

          <!-- Modal Footer -->
          <div class="flex justify-end gap-2 p-4 border-t border-discord-bg-tertiary">
            <Button @click="closeGenreModal" variant="ghost" size="sm">Cancel</Button>
            <Button @click="addGenre" size="sm">Add Genre</Button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Delete Confirmation Popup Modal -->
    <Transition
      enter-active-class="transition-all duration-200 ease-out"
      enter-from-class="opacity-0 scale-95"
      enter-to-class="opacity-100 scale-100"
      leave-active-class="transition-all duration-150 ease-in"
      leave-from-class="opacity-100 scale-100"
      leave-to-class="opacity-0 scale-95"
    >
      <div
        v-if="showDeleteModal"
        class="fixed inset-0 z-[150] flex items-center justify-center p-4"
        @click.self="closeDeleteModal"
      >
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm"></div>

        <!-- Modal Content -->
        <div class="relative bg-discord-bg-secondary rounded-xl shadow-2xl border border-discord-bg-tertiary w-full max-w-sm p-6">
          <div class="text-center">
            <!-- Warning Icon -->
            <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-500/20 mb-4">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>

            <h3 class="text-lg font-bold text-white mb-2">Delete Genre</h3>
            <p class="text-discord-text-secondary text-sm mb-6">
              Are you sure you want to delete this genre? This action cannot be undone.
            </p>

            <!-- Buttons -->
            <div class="flex gap-3 justify-center">
              <Button @click="closeDeleteModal" variant="ghost" size="sm">Cancel</Button>
              <Button @click="confirmDelete" variant="danger" size="sm">Delete</Button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>
