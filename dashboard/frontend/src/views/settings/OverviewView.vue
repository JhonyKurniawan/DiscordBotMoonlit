<script setup>
import { onMounted, watch, computed, onBeforeUnmount, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'
import { useGuildStore } from '@/stores/guild'
import Card from '@/components/ui/Card.vue'
import Toggle from '@/components/ui/Toggle.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Button from '@/components/ui/Button.vue'
import ImagePreview from '@/components/ui/ImagePreview.vue'
import FileUpload from '@/components/ui/FileUpload.vue'
import RangeInput from '@/components/ui/RangeInput.vue'
import TextStyleSelector from '@/components/ui/TextStyleSelector.vue'
import RoleSelector from '@/components/ui/RoleSelector.vue'
import ColorInput from '@/components/ui/ColorInput.vue'

const route = useRoute()
const settingsStore = useSettingsStore()
const guildStore = useGuildStore()

const guildId = computed(() => route.params.guildId)

// Channel options
const channelOptions = computed(() => guildStore.getChannelOptions(guildId.value))

// Role options
const roleOptions = computed(() => guildStore.getRoleOptions(guildId.value))

// Convert channel IDs to strings for proper comparison with options
const welcomeChannelId = computed(() => String(settingsStore.guildSettings.welcome_channel_id || ''))
const goodbyeChannelId = computed(() => String(settingsStore.guildSettings.goodbye_channel_id || ''))

// Auto role IDs as array
const autoRoleIds = computed(() => {
  const ids = settingsStore.guildSettings.auto_role_ids
  if (!ids) return []

  // Backend returns array, handle both array and string
  if (Array.isArray(ids)) {
    return ids.map(id => String(id)).filter(id => id)
  }
  if (typeof ids === 'string' && ids.trim()) {
    return ids.split(',').map(id => id.trim()).filter(id => id)
  }
  return []
})

// Check if a role is selected
function isRoleSelected(roleId) {
  return autoRoleIds.value.includes(roleId)
}

// Toggle role selection with auto-save
async function toggleAutoRole(roleId) {
  const currentIds = autoRoleIds.value
  const index = currentIds.indexOf(roleId)
  if (index > -1) {
    // Remove if already selected
    currentIds.splice(index, 1)
  } else {
    // Add if not selected
    currentIds.push(roleId)
  }
  // Update settings store
  settingsStore.guildSettings.auto_role_ids = currentIds.join(',')
  // Auto-save
  await settingsStore.saveGuildSettings(guildId.value)
  // Reload settings from server to get the confirmed state
  await settingsStore.loadGuildSettings(guildId.value)
  // Reset original settings after reload
  resetOriginalSettings()
}
const imagePreviewKey = computed(() => {
  return JSON.stringify({
    bannerUrl: settingsStore.guildSettings.banner_url,
    welcomeText: settingsStore.guildSettings.welcome_text,
    text: settingsStore.guildSettings.welcome_message,
    textColor: settingsStore.guildSettings.text_color,
    profilePosition: settingsStore.guildSettings.profile_position,
    welcomeTextSize: settingsStore.guildSettings.welcome_text_size,
    usernameTextSize: settingsStore.guildSettings.username_text_size,
    avatarSize: settingsStore.guildSettings.avatar_size,
    // Text styles
    welcomeTextBold: settingsStore.guildSettings.welcome_text_bold,
    welcomeTextItalic: settingsStore.guildSettings.welcome_text_italic,
    welcomeTextUnderline: settingsStore.guildSettings.welcome_text_underline,
    usernameTextBold: settingsStore.guildSettings.username_text_bold,
    usernameTextItalic: settingsStore.guildSettings.username_text_italic,
    usernameTextUnderline: settingsStore.guildSettings.username_text_underline,
    googleFontFamily: settingsStore.guildSettings.google_font_family,
    customFontPath: settingsStore.guildSettings.custom_font_path,
    avatarShape: settingsStore.guildSettings.avatar_shape,
    avatarBorderEnabled: settingsStore.guildSettings.avatar_border_enabled,
    avatarBorderWidth: settingsStore.guildSettings.avatar_border_width,
    avatarBorderColor: settingsStore.guildSettings.avatar_border_color || '#FFFFFF'
  })
})

// Key for Goodbye ImagePreview
const goodbyeImagePreviewKey = computed(() => {
  return JSON.stringify({
    bannerUrl: settingsStore.guildSettings.goodbye_banner_url || settingsStore.guildSettings.banner_url,
    welcomeText: settingsStore.guildSettings.goodbye_text || 'GOODBYE',
    text: settingsStore.guildSettings.goodbye_message || 'Goodbye {user}!',
    textColor: settingsStore.guildSettings.goodbye_text_color || '#FF6B6B',
    profilePosition: settingsStore.guildSettings.goodbye_profile_position || 'center',
    welcomeTextSize: settingsStore.guildSettings.goodbye_welcome_text_size || 56,
    usernameTextSize: settingsStore.guildSettings.goodbye_username_text_size || 32,
    avatarSize: settingsStore.guildSettings.goodbye_avatar_size || 180,
    // Text styles
    welcomeTextBold: settingsStore.guildSettings.goodbye_text_bold,
    welcomeTextItalic: settingsStore.guildSettings.goodbye_text_italic,
    welcomeTextUnderline: settingsStore.guildSettings.goodbye_text_underline,
    usernameTextBold: settingsStore.guildSettings.goodbye_username_text_bold,
    usernameTextItalic: settingsStore.guildSettings.goodbye_username_text_italic,
    usernameTextUnderline: settingsStore.guildSettings.goodbye_username_text_underline,
    googleFontFamily: settingsStore.guildSettings.google_font_family,
    customFontPath: settingsStore.guildSettings.custom_font_path,
    avatarShape: settingsStore.guildSettings.goodbye_avatar_shape,
    avatarBorderEnabled: settingsStore.guildSettings.goodbye_avatar_border_enabled,
    avatarBorderWidth: settingsStore.guildSettings.goodbye_avatar_border_width,
    avatarBorderColor: settingsStore.guildSettings.goodbye_avatar_border_color || '#FFFFFF'
  })
})

let isLoading = false

// Store original settings for change detection
const originalSettings = ref('')

// Check if there are unsaved changes
const hasUnsavedChanges = computed(() => {
  if (!originalSettings.value) return false
  const currentSettings = JSON.stringify(settingsStore.guildSettings)
  return currentSettings !== originalSettings.value
})

// Reset original settings after save
function resetOriginalSettings() {
  originalSettings.value = JSON.stringify(settingsStore.guildSettings)
}

onMounted(() => {
  // Don't await - load in background
  loadSettings()
  loadChannels()
  loadRoles()
})

// Only watch guildId changes, not initial mount
watch(guildId, (newId, oldId) => {
  if (oldId && newId !== oldId) {
    originalSettings.value = '' // Reset when changing guild
    loadSettings()
    loadChannels()
    loadRoles()
  }
}, { flush: 'post' })

async function loadSettings() {
  if (isLoading) return
  isLoading = true
  try {
    await settingsStore.loadGuildSettings(guildId.value)
    // Set original settings after loading
    originalSettings.value = JSON.stringify(settingsStore.guildSettings)
  } finally {
    isLoading = false
  }
}

async function loadChannels() {
  if (guildId.value) {
    guildStore.loadChannels(guildId.value)
  }
}

async function loadRoles() {
  if (guildId.value) {
    guildStore.loadRoles(guildId.value)
  }
}

async function saveSettings() {
  const success = await settingsStore.saveGuildSettings(guildId.value)
  if (success) {
    resetOriginalSettings()
  }
}

onBeforeUnmount(() => {
  isLoading = false
})
</script>

<template>
  <div class="space-y-6 pb-24">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 bg-gradient-to-br from-discord-green to-emerald-600 rounded-xl flex items-center justify-center shadow-lg">
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
          </svg>
        </div>
        <div>
          <h2 class="text-xl font-bold text-white">General Settings</h2>
          <p class="text-discord-text-secondary text-sm">Configure welcome messages and auto roles</p>
        </div>
      </div>
    </div>

    <!-- Welcome Settings -->
    <Card>
      <template #title>
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-discord-green" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 11.5V14m0-2.5v-6a1.5 1.5 0 113 0m-3 6a1.5 1.5 0 00-3 0v2a7.5 7.5 0 0015 0v-5a1.5 1.5 0 00-3 0m-6-3V11m0-5.5v-1a1.5 1.5 0 013 0v1m0 0V11m0-5.5a1.5 1.5 0 013 0v3m0 0V11"/>
          </svg>
          <span>Welcome Messages</span>
        </div>
      </template>
      <div class="space-y-4">
        <Toggle
          :model-value="settingsStore.guildSettings.welcome_enabled"
          @update:model-value="(v) => settingsStore.guildSettings.welcome_enabled = v"
          label="Enable Welcome Messages"
          description="Send a welcome message when someone joins the server"
        />

        <div v-if="settingsStore.guildSettings.welcome_enabled" class="pl-4 space-y-4 border-l-2 border-discord-bg-tertiary">
          <Select
            :model-value="welcomeChannelId"
            @update:model-value="(v) => settingsStore.guildSettings.welcome_channel_id = v || null"
            label="Welcome Channel"
            placeholder="Select a channel for welcome messages"
            :options="channelOptions"
          />

          <Input
            :model-value="settingsStore.guildSettings.welcome_message"
            @update:model-value="(v) => settingsStore.guildSettings.welcome_message = v"
            label="Welcome Message"
            placeholder="Welcome {user} to the server!"
          />
        </div>
      </div>
    </Card>

    <!-- Goodbye Settings -->
    <Card>
      <template #title>
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-discord-red" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
          </svg>
          <span>Goodbye Messages</span>
        </div>
      </template>
      <div class="space-y-4">
        <Toggle
          :model-value="settingsStore.guildSettings.goodbye_enabled || false"
          @update:model-value="(v) => settingsStore.guildSettings.goodbye_enabled = v"
          label="Enable Goodbye Messages"
          description="Send a goodbye message when someone leaves the server"
        />

        <div v-if="settingsStore.guildSettings.goodbye_enabled" class="pl-4 space-y-4 border-l-2 border-discord-bg-tertiary">
          <Select
            :model-value="goodbyeChannelId"
            @update:model-value="(v) => settingsStore.guildSettings.goodbye_channel_id = v || null"
            label="Goodbye Channel"
            placeholder="Select a channel for goodbye messages"
            :options="channelOptions"
          />

          <Input
            :model-value="settingsStore.guildSettings.goodbye_message || 'Goodbye {user}!'"
            @update:model-value="(v) => settingsStore.guildSettings.goodbye_message = v"
            label="Goodbye Message"
            placeholder="Goodbye {user}!"
          />
        </div>
      </div>
    </Card>

    <!-- Welcome Image Settings -->
    <Card>
      <template #title>
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-discord-blurple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
          </svg>
          <span>Welcome Image</span>
        </div>
      </template>
      <div class="space-y-4">
        <Toggle
          :model-value="settingsStore.guildSettings.use_image"
          @update:model-value="(v) => settingsStore.guildSettings.use_image = v"
          label="Enable Welcome Image"
          description="Send a generated image when someone joins"
        />

        <div v-if="settingsStore.guildSettings.use_image" class="space-y-6">
          
          <!-- Layout & Background Section -->
          <div class="space-y-4 pt-2">
            <h4 class="flex items-center gap-2 text-sm font-semibold text-discord-text-primary border-b border-discord-bg-tertiary pb-2">
              <svg class="w-4 h-4 text-discord-blurple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
              </svg>
              Layout & Background
            </h4>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Toggle
                :model-value="settingsStore.guildSettings.send_banner_as_is"
                @update:model-value="(v) => settingsStore.guildSettings.send_banner_as_is = v"
                label="Send Banner As-Is (Custom Design)"
                description="Send banner directly without adding avatar/text."
              />

              <Toggle
                :model-value="settingsStore.guildSettings.send_gif_as_is"
                @update:model-value="(v) => settingsStore.guildSettings.send_gif_as_is = v"
                label="Animated GIF Support"
                description="Process as animated GIF (slower generation)."
              />
            </div>

            <!-- File Upload with URL option -->
            <FileUpload
              :model-value="settingsStore.guildSettings.banner_url"
              @update:model-value="(v) => settingsStore.guildSettings.banner_url = v"
              label="Background Image"
              placeholder="Upload an image or enter URL"
            />
          </div>

          <!-- Message & Text Section -->
          <div class="space-y-4 pt-2">
            <h4 class="flex items-center gap-2 text-sm font-semibold text-discord-text-primary border-b border-discord-bg-tertiary pb-2">
              <svg class="w-4 h-4 text-discord-blurple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
              </svg>
              Message & Text
            </h4>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                :model-value="settingsStore.guildSettings.welcome_text"
                @update:model-value="(v) => settingsStore.guildSettings.welcome_text = v"
                label="Big Text"
                placeholder="WELCOME"
              />

              <ColorInput
                :model-value="settingsStore.guildSettings.text_color"
                @update:model-value="(v) => settingsStore.guildSettings.text_color = v"
                label="Text Color"
                placeholder="#FFD700"
              />
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Select
                :model-value="settingsStore.guildSettings.font_family || 'arial'"
                @update:model-value="(v) => settingsStore.guildSettings.font_family = v"
                label="Font"
                :font-preview="true"
                :grouped="true"
                :options="[
                  { value: 'arial', label: 'Arial', group: 'Sans-Serif' },
                  { value: 'verdana', label: 'Verdana', group: 'Sans-Serif' },
                  { value: 'comic', label: 'Comic Sans MS', group: 'Sans-Serif' },
                  { value: 'segoe', label: 'Segoe UI', group: 'Sans-Serif' },
                  { value: 'tahoma', label: 'Tahoma', group: 'Sans-Serif' },
                  { value: 'trebuchet', label: 'Trebuchet MS', group: 'Sans-Serif' },
                  { value: 'calibri', label: 'Calibri', group: 'Sans-Serif' },
                  { value: 'franklin', label: 'Franklin Gothic', group: 'Sans-Serif' },
                  { value: 'roboto', label: 'Roboto', group: 'Sans-Serif (Google)' },
                  { value: 'poppins', label: 'Poppins', group: 'Sans-Serif (Google)' },
                  { value: 'montserrat', label: 'Montserrat', group: 'Sans-Serif (Google)' },
                  { value: 'opensans', label: 'Open Sans', group: 'Sans-Serif (Google)' },
                  { value: 'lato', label: 'Lato', group: 'Sans-Serif (Google)' },
                  { value: 'oswald', label: 'Oswald', group: 'Sans-Serif (Google)' },
                  { value: 'raleway', label: 'Raleway', group: 'Sans-Serif (Google)' },
                  { value: 'ptsans', label: 'PT Sans', group: 'Sans-Serif (Google)' },
                  { value: 'nunito', label: 'Nunito', group: 'Sans-Serif (Google)' },
                  { value: 'georgia', label: 'Georgia', group: 'Serif' },
                  { value: 'times', label: 'Times New Roman', group: 'Serif' },
                  { value: 'palatino', label: 'Palatino Linotype', group: 'Serif' },
                  { value: 'cambria', label: 'Cambria', group: 'Serif' },
                  { value: 'century', label: 'Century', group: 'Serif' },
                  { value: 'rockwell', label: 'Rockwell', group: 'Serif' },
                  { value: 'courier', label: 'Courier New', group: 'Monospace' },
                  { value: 'consolas', label: 'Consolas', group: 'Monospace' },
                  { value: 'lucida', label: 'Lucida Console', group: 'Monospace' },
                  { value: 'arialblack', label: 'Arial Black', group: 'Display' },
                  { value: 'impact', label: 'Impact', group: 'Display' },
                  { value: 'bebasneue', label: 'Bebas Neue', group: 'Display (Google)' }
                ]"
              />
            </div>
          </div>

          <!-- Avatar Styling Section -->
          <div class="space-y-4 pt-2">
            <h4 class="flex items-center gap-2 text-sm font-semibold text-discord-text-primary border-b border-discord-bg-tertiary pb-2">
              <svg class="w-4 h-4 text-discord-blurple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              Avatar Styling
            </h4>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Select
                :model-value="settingsStore.guildSettings.avatar_shape || 'circle'"
                @update:model-value="(v) => settingsStore.guildSettings.avatar_shape = v"
                label="Avatar Shape"
                :options="[
                  { value: 'circle', label: 'Circle' },
                  { value: 'rounded', label: 'Rounded Square' },
                  { value: 'square', label: 'Square' },
                  { value: 'squircle', label: 'Squircle' },
                  { value: 'hexagon', label: 'Hexagon' },
                  { value: 'star', label: 'Star' },
                  { value: 'diamond', label: 'Diamond' },
                  { value: 'triangle', label: 'Triangle' }
                ]"
              />

              <Toggle
                :model-value="settingsStore.guildSettings.avatar_border_enabled !== undefined ? settingsStore.guildSettings.avatar_border_enabled : true"
                @update:model-value="(v) => settingsStore.guildSettings.avatar_border_enabled = v"
                label="Avatar Border"
              />
            </div>
          
            <div 
              v-if="settingsStore.guildSettings.avatar_border_enabled !== undefined ? settingsStore.guildSettings.avatar_border_enabled : true"
              class="grid grid-cols-1 md:grid-cols-2 gap-4"
            >
              <RangeInput
                :model-value="settingsStore.guildSettings.avatar_border_width || 6"
                @update:model-value="(v) => settingsStore.guildSettings.avatar_border_width = v"
                label="Border Width"
                :min="1"
                :max="20"
                :default="6"
                unit="px"
              />

              <ColorInput
                :model-value="settingsStore.guildSettings.avatar_border_color || '#FFFFFF'"
                @update:model-value="(v) => settingsStore.guildSettings.avatar_border_color = v"
                label="Border Color"
                placeholder="#FFFFFF"
              />
            </div>
          </div>

          <!-- Text Style Section -->
          <div class="space-y-4 pt-2">
            <h4 class="flex items-center gap-2 text-sm font-semibold text-discord-text-primary border-b border-discord-bg-tertiary pb-2">
              <svg class="w-4 h-4 text-discord-blurple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16m-7 6h7"/>
              </svg>
              Text Style & Size
            </h4>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <TextStyleSelector
                label="Welcome Text (WELCOME)"
                :bold="settingsStore.guildSettings.welcome_text_bold"
                :italic="settingsStore.guildSettings.welcome_text_italic"
                :underline="settingsStore.guildSettings.welcome_text_underline"
                @update:bold="(v) => settingsStore.guildSettings.welcome_text_bold = v"
                @update:italic="(v) => settingsStore.guildSettings.welcome_text_italic = v"
                @update:underline="(v) => settingsStore.guildSettings.welcome_text_underline = v"
              />

              <TextStyleSelector
                label="Username Text"
                :bold="settingsStore.guildSettings.username_text_bold"
                :italic="settingsStore.guildSettings.username_text_italic"
                :underline="settingsStore.guildSettings.username_text_underline"
                @update:bold="(v) => settingsStore.guildSettings.username_text_bold = v"
                @update:italic="(v) => settingsStore.guildSettings.username_text_italic = v"
                @update:underline="(v) => settingsStore.guildSettings.username_text_underline = v"
              />
            </div>
          </div>

          <!-- Advanced Positioning & Sizing Section -->
          <div class="space-y-4 pt-2">
            <h4 class="flex items-center gap-2 text-sm font-semibold text-discord-text-primary border-b border-discord-bg-tertiary pb-2">
              <svg class="w-4 h-4 text-discord-blurple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"/>
              </svg>
              Advanced Sizing & Positioning
            </h4>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-6">
              <!-- Text Sizes -->
              <div class="space-y-4">
                <h5 class="text-xs font-semibold text-discord-text-secondary uppercase">Text Sizes</h5>
                <RangeInput
                  :model-value="settingsStore.guildSettings.welcome_text_size || 56"
                  @update:model-value="(v) => settingsStore.guildSettings.welcome_text_size = v"
                  @reset="(v) => settingsStore.guildSettings.welcome_text_size = v"
                  label="Welcome Text Size"
                  :min="30"
                  :max="100"
                  :step="1"
                  :default="56"
                />

                <RangeInput
                  :model-value="settingsStore.guildSettings.username_text_size || 32"
                  @update:model-value="(v) => settingsStore.guildSettings.username_text_size = v"
                  @reset="(v) => settingsStore.guildSettings.username_text_size = v"
                  label="Username Text Size"
                  :min="20"
                  :max="60"
                  :step="1"
                  :default="32"
                />
              </div>

              <!-- Avatar Size -->
              <div class="space-y-4">
                <h5 class="text-xs font-semibold text-discord-text-secondary uppercase">Avatar Size</h5>
                <RangeInput
                  :model-value="settingsStore.guildSettings.avatar_size || 180"
                  @update:model-value="(v) => settingsStore.guildSettings.avatar_size = v"
                  @reset="(v) => settingsStore.guildSettings.avatar_size = v"
                  label="Avatar Size"
                  :min="100"
                  :max="250"
                  :step="5"
                  :default="180"
                />
              </div>

              <!-- Banner Position -->
              <div class="space-y-2">
                <h5 class="text-xs font-semibold text-discord-text-secondary uppercase">Banner Offset</h5>
                <div class="grid grid-cols-2 gap-2">
                  <Input
                    :model-value="settingsStore.guildSettings.banner_offset_x"
                    @update:model-value="(v) => settingsStore.guildSettings.banner_offset_x = v"
                    label="X Offset"
                    type="number"
                    placeholder="0"
                  />
                  <Input
                    :model-value="settingsStore.guildSettings.banner_offset_y"
                    @update:model-value="(v) => settingsStore.guildSettings.banner_offset_y = v"
                    label="Y Offset"
                    type="number"
                    placeholder="0"
                  />
                </div>
              </div>

              <!-- Avatar Position -->
              <div class="space-y-2">
                <h5 class="text-xs font-semibold text-discord-text-secondary uppercase">Avatar Position</h5>
                <div class="grid grid-cols-2 gap-2">
                  <Input
                    :model-value="settingsStore.guildSettings.avatar_offset_x"
                    @update:model-value="(v) => settingsStore.guildSettings.avatar_offset_x = v"
                    label="X Position"
                    type="number"
                    placeholder="0"
                  />
                  <Input
                    :model-value="settingsStore.guildSettings.avatar_offset_y"
                    @update:model-value="(v) => settingsStore.guildSettings.avatar_offset_y = v"
                    label="Y Position"
                    type="number"
                    placeholder="0"
                  />
                </div>
              </div>

              <!-- Text Position -->
              <div class="space-y-2 col-span-1 md:col-span-2">
                <h5 class="text-xs font-semibold text-discord-text-secondary uppercase">Text Position</h5>
                <div class="grid grid-cols-2 gap-2">
                  <Input
                    :model-value="settingsStore.guildSettings.text_offset_x"
                    @update:model-value="(v) => settingsStore.guildSettings.text_offset_x = v"
                    label="X Position"
                    type="number"
                    placeholder="0"
                  />
                  <Input
                    :model-value="settingsStore.guildSettings.text_offset_y"
                    @update:model-value="(v) => settingsStore.guildSettings.text_offset_y = v"
                    label="Y Position"
                    type="number"
                    placeholder="0"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- Image Preview -->
          <ImagePreview
            :key="imagePreviewKey"
            :banner-url="settingsStore.guildSettings.banner_url"
            :welcome-text="settingsStore.guildSettings.welcome_text"
            :text="settingsStore.guildSettings.welcome_message"
            :text-color="settingsStore.guildSettings.text_color"
            :profile-position="settingsStore.guildSettings.profile_position"
            :font-family="settingsStore.guildSettings.font_family"
            :avatar-offset-x="settingsStore.guildSettings.avatar_offset_x ?? 0"
            :avatar-offset-y="settingsStore.guildSettings.avatar_offset_y ?? -25"
            :text-offset-x="settingsStore.guildSettings.text_offset_x ?? 0"
            :text-offset-y="settingsStore.guildSettings.text_offset_y ?? 125"
            :welcome-text-size="settingsStore.guildSettings.welcome_text_size ?? 56"
            :username-text-size="settingsStore.guildSettings.username_text_size ?? 32"
            :avatar-size="settingsStore.guildSettings.avatar_size ?? 180"
            :welcome-text-bold="settingsStore.guildSettings.welcome_text_bold"
            :welcome-text-italic="settingsStore.guildSettings.welcome_text_italic"
            :welcome-text-underline="settingsStore.guildSettings.welcome_text_underline"
            :username-text-bold="settingsStore.guildSettings.username_text_bold"
            :username-text-italic="settingsStore.guildSettings.username_text_italic"
            :username-text-underline="settingsStore.guildSettings.username_text_underline"
            :google-font-family="settingsStore.guildSettings.google_font_family"
            :custom-font-path="settingsStore.guildSettings.custom_font_path"
            :avatar-shape="settingsStore.guildSettings.avatar_shape || 'circle'"
            :avatar-border-enabled="settingsStore.guildSettings.avatar_border_enabled !== undefined ? settingsStore.guildSettings.avatar_border_enabled : true"
            :avatar-border-width="settingsStore.guildSettings.avatar_border_width || 6"
            :avatar-border-color="settingsStore.guildSettings.avatar_border_color || '#FFFFFF'"
            @update:avatar-offset-x="(v) => settingsStore.guildSettings.avatar_offset_x = v"
            @update:avatar-offset-y="(v) => settingsStore.guildSettings.avatar_offset_y = v"
            @update:text-offset-x="(v) => settingsStore.guildSettings.text_offset_x = v"
            @update:text-offset-y="(v) => settingsStore.guildSettings.text_offset_y = v"
          />
        </div>
      </div>
    </Card>

    <!-- Goodbye Image Settings -->
    <Card>
      <template #title>
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-discord-blurple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
          </svg>
          <span>Goodbye Image</span>
        </div>
      </template>
      <div class="space-y-4">
        <Toggle
          :model-value="settingsStore.guildSettings.use_goodbye_image"
          @update:model-value="(v) => settingsStore.guildSettings.use_goodbye_image = v"
          label="Enable Goodbye Image (Separate from Welcome)"
          description="When enabled, use separate settings for goodbye images. When disabled, goodbye uses welcome settings with 'GOODBYE' text."
        />

        <div v-if="settingsStore.guildSettings.use_goodbye_image" class="space-y-6">
          
          <!-- Layout & Background Section -->
          <div class="space-y-4 pt-2">
            <h4 class="flex items-center gap-2 text-sm font-semibold text-discord-text-primary border-b border-discord-bg-tertiary pb-2">
              <svg class="w-4 h-4 text-discord-blurple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
              </svg>
              Layout & Background
            </h4>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Toggle
                :model-value="settingsStore.guildSettings.goodbye_send_banner_as_is"
                @update:model-value="(v) => settingsStore.guildSettings.goodbye_send_banner_as_is = v"
                label="Send Banner As-Is (Custom Design)"
                description="Send banner directly without adding avatar/text."
              />

              <Toggle
                :model-value="settingsStore.guildSettings.goodbye_send_gif_as_is"
                @update:model-value="(v) => settingsStore.guildSettings.goodbye_send_gif_as_is = v"
                label="Animated GIF Support"
                description="Process as animated GIF (slower generation)."
              />
            </div>

            <!-- File Upload with URL option -->
            <FileUpload
              :model-value="settingsStore.guildSettings.goodbye_banner_url"
              @update:model-value="(v) => settingsStore.guildSettings.goodbye_banner_url = v"
              label="Background Image (Leave empty to use welcome banner)"
              placeholder="Upload an image or enter URL"
            />
          </div>

          <!-- Message & Text Section -->
          <div class="space-y-4 pt-2">
            <h4 class="flex items-center gap-2 text-sm font-semibold text-discord-text-primary border-b border-discord-bg-tertiary pb-2">
              <svg class="w-4 h-4 text-discord-blurple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
              </svg>
              Message & Text
            </h4>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                :model-value="settingsStore.guildSettings.goodbye_text"
                @update:model-value="(v) => settingsStore.guildSettings.goodbye_text = v"
                label="Big Text"
                placeholder="GOODBYE"
              />

              <ColorInput
                :model-value="settingsStore.guildSettings.goodbye_text_color || '#FF6B6B'"
                @update:model-value="(v) => settingsStore.guildSettings.goodbye_text_color = v"
                label="Text Color"
                placeholder="#FF6B6B"
              />
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">

            <Select
              :model-value="settingsStore.guildSettings.goodbye_font_family || 'arial'"
              @update:model-value="(v) => settingsStore.guildSettings.goodbye_font_family = v"
              label="Font"
              :font-preview="true"
              :grouped="true"
              :options="[
                { value: 'arial', label: 'Arial', group: 'Sans-Serif' },
                { value: 'verdana', label: 'Verdana', group: 'Sans-Serif' },
                { value: 'comic', label: 'Comic Sans MS', group: 'Sans-Serif' },
                { value: 'segoe', label: 'Segoe UI', group: 'Sans-Serif' },
                { value: 'tahoma', label: 'Tahoma', group: 'Sans-Serif' },
                { value: 'trebuchet', label: 'Trebuchet MS', group: 'Sans-Serif' },
                { value: 'calibri', label: 'Calibri', group: 'Sans-Serif' },
                { value: 'franklin', label: 'Franklin Gothic', group: 'Sans-Serif' },
                { value: 'roboto', label: 'Roboto', group: 'Sans-Serif (Google)' },
                { value: 'poppins', label: 'Poppins', group: 'Sans-Serif (Google)' },
                { value: 'montserrat', label: 'Montserrat', group: 'Sans-Serif (Google)' },
                { value: 'opensans', label: 'Open Sans', group: 'Sans-Serif (Google)' },
                { value: 'lato', label: 'Lato', group: 'Sans-Serif (Google)' },
                { value: 'oswald', label: 'Oswald', group: 'Sans-Serif (Google)' },
                { value: 'raleway', label: 'Raleway', group: 'Sans-Serif (Google)' },
                { value: 'ptsans', label: 'PT Sans', group: 'Sans-Serif (Google)' },
                { value: 'nunito', label: 'Nunito', group: 'Sans-Serif (Google)' },
                { value: 'georgia', label: 'Georgia', group: 'Serif' },
                { value: 'times', label: 'Times New Roman', group: 'Serif' },
                { value: 'palatino', label: 'Palatino Linotype', group: 'Serif' },
                { value: 'cambria', label: 'Cambria', group: 'Serif' },
                { value: 'century', label: 'Century', group: 'Serif' },
                { value: 'rockwell', label: 'Rockwell', group: 'Serif' },
                { value: 'courier', label: 'Courier New', group: 'Monospace' },
                { value: 'consolas', label: 'Consolas', group: 'Monospace' },
                { value: 'lucida', label: 'Lucida Console', group: 'Monospace' },
                { value: 'arialblack', label: 'Arial Black', group: 'Display' },
                { value: 'impact', label: 'Impact', group: 'Display' },
                { value: 'bebasneue', label: 'Bebas Neue', group: 'Display (Google)' }
              ]"
            />
            </div>
          </div>

          <!-- Avatar Styling Section -->
          <div class="space-y-4 pt-2">
            <h4 class="flex items-center gap-2 text-sm font-semibold text-discord-text-primary border-b border-discord-bg-tertiary pb-2">
              <svg class="w-4 h-4 text-discord-blurple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              Avatar Styling
            </h4>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Select
                :model-value="settingsStore.guildSettings.goodbye_avatar_shape || 'circle'"
                @update:model-value="(v) => settingsStore.guildSettings.goodbye_avatar_shape = v"
                label="Avatar Shape"
                :options="[
                  { value: 'circle', label: 'Circle' },
                  { value: 'rounded', label: 'Rounded Square' },
                  { value: 'square', label: 'Square' },
                  { value: 'squircle', label: 'Squircle' },
                  { value: 'hexagon', label: 'Hexagon' },
                  { value: 'star', label: 'Star' },
                  { value: 'diamond', label: 'Diamond' },
                  { value: 'triangle', label: 'Triangle' }
                ]"
              />

              <Toggle
                :model-value="settingsStore.guildSettings.goodbye_avatar_border_enabled !== undefined ? settingsStore.guildSettings.goodbye_avatar_border_enabled : true"
                @update:model-value="(v) => settingsStore.guildSettings.goodbye_avatar_border_enabled = v"
                label="Avatar Border"
              />
            </div>

            <div 
              v-if="settingsStore.guildSettings.goodbye_avatar_border_enabled !== undefined ? settingsStore.guildSettings.goodbye_avatar_border_enabled : true"
              class="grid grid-cols-1 md:grid-cols-2 gap-4"
            >
              <RangeInput
                :model-value="settingsStore.guildSettings.goodbye_avatar_border_width || 6"
                @update:model-value="(v) => settingsStore.guildSettings.goodbye_avatar_border_width = v"
                label="Border Width"
                :min="1"
                :max="20"
                :default="6"
                unit="px"
              />

              <ColorInput
                :model-value="settingsStore.guildSettings.goodbye_avatar_border_color || '#FFFFFF'"
                @update:model-value="(v) => settingsStore.guildSettings.goodbye_avatar_border_color = v"
                label="Border Color"
                placeholder="#FFFFFF"
              />
            </div>
          </div>

          <!-- Text Style Settings for Goodbye -->
          <!-- Text Style Section -->
          <div class="space-y-4 pt-2">
            <h4 class="flex items-center gap-2 text-sm font-semibold text-discord-text-primary border-b border-discord-bg-tertiary pb-2">
              <svg class="w-4 h-4 text-discord-blurple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16m-7 6h7"/>
              </svg>
              Text Style & Size
            </h4>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <TextStyleSelector
                label="Goodbye Text (GOODBYE)"
                :bold="settingsStore.guildSettings.goodbye_text_bold"
                :italic="settingsStore.guildSettings.goodbye_text_italic"
                :underline="settingsStore.guildSettings.goodbye_text_underline"
                @update:bold="(v) => settingsStore.guildSettings.goodbye_text_bold = v"
                @update:italic="(v) => settingsStore.guildSettings.goodbye_text_italic = v"
                @update:underline="(v) => settingsStore.guildSettings.goodbye_text_underline = v"
              />

              <TextStyleSelector
                label="Username Text"
                :bold="settingsStore.guildSettings.goodbye_username_text_bold"
                :italic="settingsStore.guildSettings.goodbye_username_text_italic"
                :underline="settingsStore.guildSettings.goodbye_username_text_underline"
                @update:bold="(v) => settingsStore.guildSettings.goodbye_username_text_bold = v"
                @update:italic="(v) => settingsStore.guildSettings.goodbye_username_text_italic = v"
                @update:underline="(v) => settingsStore.guildSettings.goodbye_username_text_underline = v"
              />
            </div>
          </div>

          <!-- Advanced Positioning & Sizing Section -->
          <div class="space-y-4 pt-2">
            <h4 class="flex items-center gap-2 text-sm font-semibold text-discord-text-primary border-b border-discord-bg-tertiary pb-2">
              <svg class="w-4 h-4 text-discord-blurple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"/>
              </svg>
              Advanced Sizing & Positioning
            </h4>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-6">
              <!-- Text Sizes -->
              <div class="space-y-4">
                <h5 class="text-xs font-semibold text-discord-text-secondary uppercase">Text Sizes</h5>
                <RangeInput
                  :model-value="settingsStore.guildSettings.goodbye_welcome_text_size || 56"
                  @update:model-value="(v) => settingsStore.guildSettings.goodbye_welcome_text_size = v"
                  @reset="(v) => settingsStore.guildSettings.goodbye_welcome_text_size = v"
                  label="Goodbye Text Size"
                  :min="30"
                  :max="100"
                  :step="1"
                  :default="56"
                />

                <RangeInput
                  :model-value="settingsStore.guildSettings.goodbye_username_text_size || 32"
                  @update:model-value="(v) => settingsStore.guildSettings.goodbye_username_text_size = v"
                  @reset="(v) => settingsStore.guildSettings.goodbye_username_text_size = v"
                  label="Username Text Size"
                  :min="20"
                  :max="60"
                  :step="1"
                  :default="32"
                />
              </div>

              <!-- Avatar Size -->
              <div class="space-y-4">
                <h5 class="text-xs font-semibold text-discord-text-secondary uppercase">Avatar Size</h5>
                <RangeInput
                  :model-value="settingsStore.guildSettings.goodbye_avatar_size || 180"
                  @update:model-value="(v) => settingsStore.guildSettings.goodbye_avatar_size = v"
                  @reset="(v) => settingsStore.guildSettings.goodbye_avatar_size = v"
                  label="Avatar Size"
                  :min="100"
                  :max="250"
                  :step="5"
                  :default="180"
                />
              </div>

              <!-- Banner Position -->
              <div class="space-y-2">
                <h5 class="text-xs font-semibold text-discord-text-secondary uppercase">Banner Offset</h5>
                <div class="grid grid-cols-2 gap-2">
                  <Input
                    :model-value="settingsStore.guildSettings.goodbye_banner_offset_x"
                    @update:model-value="(v) => settingsStore.guildSettings.goodbye_banner_offset_x = v"
                    label="X Offset"
                    type="number"
                    placeholder="0"
                  />
                  <Input
                    :model-value="settingsStore.guildSettings.goodbye_banner_offset_y"
                    @update:model-value="(v) => settingsStore.guildSettings.goodbye_banner_offset_y = v"
                    label="Y Offset"
                    type="number"
                    placeholder="0"
                  />
                </div>
              </div>

              <!-- Avatar Position -->
              <div class="space-y-2">
                <h5 class="text-xs font-semibold text-discord-text-secondary uppercase">Avatar Position</h5>
                <div class="grid grid-cols-2 gap-2">
                  <Input
                    :model-value="settingsStore.guildSettings.goodbye_avatar_offset_x"
                    @update:model-value="(v) => settingsStore.guildSettings.goodbye_avatar_offset_x = v"
                    label="X Position"
                    type="number"
                    placeholder="0"
                  />
                  <Input
                    :model-value="settingsStore.guildSettings.goodbye_avatar_offset_y"
                    @update:model-value="(v) => settingsStore.guildSettings.goodbye_avatar_offset_y = v"
                    label="Y Position"
                    type="number"
                    placeholder="0"
                  />
                </div>
              </div>

              <!-- Text Position -->
              <div class="space-y-2 col-span-1 md:col-span-2">
                <h5 class="text-xs font-semibold text-discord-text-secondary uppercase">Text Position</h5>
                <div class="grid grid-cols-2 gap-2">
                  <Input
                    :model-value="settingsStore.guildSettings.goodbye_text_offset_x"
                    @update:model-value="(v) => settingsStore.guildSettings.goodbye_text_offset_x = v"
                    label="X Position"
                    type="number"
                    placeholder="0"
                  />
                  <Input
                    :model-value="settingsStore.guildSettings.goodbye_text_offset_y"
                    @update:model-value="(v) => settingsStore.guildSettings.goodbye_text_offset_y = v"
                    label="Y Position"
                    type="number"
                    placeholder="0"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- Image Preview -->
          <ImagePreview
            :key="goodbyeImagePreviewKey"
            :banner-url="settingsStore.guildSettings.goodbye_banner_url || settingsStore.guildSettings.banner_url"
            :welcome-text="settingsStore.guildSettings.goodbye_text || 'GOODBYE'"
            :text="settingsStore.guildSettings.goodbye_message || 'Goodbye {user}!'"
            :text-color="settingsStore.guildSettings.goodbye_text_color || '#FF6B6B'"
            :profile-position="settingsStore.guildSettings.goodbye_profile_position || 'center'"
            :font-family="settingsStore.guildSettings.goodbye_font_family || 'arial'"
            :avatar-offset-x="settingsStore.guildSettings.goodbye_avatar_offset_x ?? settingsStore.guildSettings.avatar_offset_x ?? 0"
            :avatar-offset-y="settingsStore.guildSettings.goodbye_avatar_offset_y ?? settingsStore.guildSettings.avatar_offset_y ?? -25"
            :text-offset-x="settingsStore.guildSettings.goodbye_text_offset_x ?? settingsStore.guildSettings.text_offset_x ?? 0"
            :text-offset-y="settingsStore.guildSettings.goodbye_text_offset_y ?? settingsStore.guildSettings.text_offset_y ?? 125"
            :welcome-text-size="settingsStore.guildSettings.goodbye_welcome_text_size ?? 56"
            :username-text-size="settingsStore.guildSettings.goodbye_username_text_size ?? 32"
            :avatar-size="settingsStore.guildSettings.goodbye_avatar_size ?? 180"
            :welcome-text-bold="settingsStore.guildSettings.goodbye_text_bold"
            :welcome-text-italic="settingsStore.guildSettings.goodbye_text_italic"
            :welcome-text-underline="settingsStore.guildSettings.goodbye_text_underline"
            :username-text-bold="settingsStore.guildSettings.goodbye_username_text_bold"
            :username-text-italic="settingsStore.guildSettings.goodbye_username_text_italic"
            :username-text-underline="settingsStore.guildSettings.goodbye_username_text_underline"
            :google-font-family="settingsStore.guildSettings.google_font_family"
            :custom-font-path="settingsStore.guildSettings.custom_font_path"
            :avatar-shape="settingsStore.guildSettings.goodbye_avatar_shape || 'circle'"
            :avatar-border-enabled="settingsStore.guildSettings.goodbye_avatar_border_enabled !== undefined ? settingsStore.guildSettings.goodbye_avatar_border_enabled : true"
            :avatar-border-width="settingsStore.guildSettings.goodbye_avatar_border_width || 6"
            :avatar-border-color="settingsStore.guildSettings.goodbye_avatar_border_color || '#FFFFFF'"
            @update:avatar-offset-x="(v) => settingsStore.guildSettings.goodbye_avatar_offset_x = v"
            @update:avatar-offset-y="(v) => settingsStore.guildSettings.goodbye_avatar_offset_y = v"
            @update:text-offset-x="(v) => settingsStore.guildSettings.goodbye_text_offset_x = v"
            @update:text-offset-y="(v) => settingsStore.guildSettings.goodbye_text_offset_y = v"
          />
        </div>
      </div>
    </Card>

    <!-- Auto Role -->
    <Card>
      <template #title>
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-discord-blurple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"/>
          </svg>
          <span>Auto Role</span>
        </div>
      </template>
      <div class="space-y-4">
        <Toggle
          :model-value="settingsStore.guildSettings.auto_role_enabled"
          @update:model-value="(v) => settingsStore.guildSettings.auto_role_enabled = v"
          label="Enable Auto Role"
          description="Automatically assign a role to new members"
        />

        <div v-if="settingsStore.guildSettings.auto_role_enabled" class="pl-4 space-y-4 border-l-2 border-discord-bg-tertiary">
          <label class="text-sm font-semibold text-discord-text-primary">Roles to Assign</label>
          <p class="text-xs text-discord-text-secondary">Select one or more roles to automatically assign to new members</p>

          <RoleSelector
            :roles="roleOptions"
            :selected-ids="autoRoleIds"
            @toggle="toggleAutoRole"
          />
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
