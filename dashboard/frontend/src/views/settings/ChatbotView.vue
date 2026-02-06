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

const route = useRoute()
const settingsStore = useSettingsStore()
const guildStore = useGuildStore()

const guildId = computed(() => route.params.guildId)

// Channel options for dropdown
const channelOptions = computed(() => guildStore.getChannelOptions(guildId.value))

// Groq AI Models with rate limits
const groqModels = [
  // Recommended for Chatting (Tier 1 - Best for Discord Bot)
  {
    value: 'llama-3.1-8b-instant',
    label: 'Llama 3.1 8B Instant',
    tier: 'recommended',
    rpm: 30,
    rpd: '14.4K',
    tpm: '6K',
    tpd: '500K',
    desc: 'Cepat & hemat quota. Cocok untuk server aktif.'
  },
  {
    value: 'llama-3.3-70b-versatile',
    label: 'Llama 3.3 70B Versatile',
    tier: 'recommended',
    rpm: 30,
    rpd: '1K',
    tpm: '12K',
    tpd: '100K',
    desc: 'Kualitas terbaik, tapi quota terbatas (1000/hari).'
  },
  {
    value: 'meta-llama/llama-4-scout-17b-16e-instruct',
    label: 'Llama 4 Scout 17B',
    tier: 'vision',
    rpm: 30,
    rpd: '1K',
    tpm: '30K',
    tpd: '500K',
    desc: 'VISION MODEL - Bisa analisis gambar. Auto-dipakai saat kirim gambar.'
  },

  // Tier 2 - Good Alternatives
  {
    value: 'meta-llama/llama-4-maverick-17b-128e-instruct',
    label: 'Llama 4 Maverick 17B',
    tier: 'vision',
    rpm: 30,
    rpd: '1K',
    tpm: '6K',
    tpd: '500K',
    desc: 'VISION MODEL - 128K context window, bisa analisis gambar.'
  },
  {
    value: 'moonshotai/kimi-k2-instruct',
    label: 'Kimi K2 Instruct',
    tier: 'good',
    rpm: 60,
    rpd: '1K',
    tpm: '10K',
    tpd: '300K',
    desc: '60 RPM limit, cocok untuk high traffic.'
  },

  // Tier 3 - Reasoning Models
  // Specialized models with explicit reasoning capabilities
  {
    value: 'openai/gpt-oss-20b',
    label: 'GPT-OSS 20B (Reasoning)',
    tier: 'reasoning',
    rpm: 30,
    rpd: '1K',
    tpm: '8K',
    tpd: '200K',
    desc: 'REASONING MODEL - Step-by-step analysis untuk soal kompleks.'
  },
  {
    value: 'openai/gpt-oss-120b',
    label: 'GPT-OSS 120B (Reasoning)',
    tier: 'reasoning',
    rpm: 30,
    rpd: '1K',
    tpm: '8K',
    tpd: '200K',
    desc: 'REASONING MODEL - 120B parameter, terbaik untuk problem solving.'
  },
  {
    value: 'qwen/qwen3-32b',
    label: 'Qwen 3 32B (Reasoning)',
    tier: 'reasoning',
    rpm: 60,
    rpd: '1K',
    tpm: '6K',
    tpd: '500K',
    desc: 'REASONING MODEL - 60 RPM, cocok untuk high traffic reasoning.'
  },

  // Tier 4 - Special Purpose
  {
    value: 'allam-2-7b',
    label: 'Allam 2 7B',
    tier: 'other',
    rpm: 30,
    rpd: '7K',
    tpm: '6K',
    tpd: '500K',
    desc: 'Model bahasa Arab.'
  },
  {
    value: 'groq/compound',
    label: 'Groq Compound',
    tier: 'other',
    rpm: 30,
    rpd: '250',
    tpm: '70K',
    tpd: 'Unlimited',
    desc: 'Special purpose model. Unlimited tokens.'
  },
  {
    value: 'groq/compound-mini',
    label: 'Groq Compound Mini',
    tier: 'other',
    rpm: 30,
    rpd: '250',
    tpm: '70K',
    tpd: 'Unlimited',
    desc: 'Special purpose model mini. Unlimited tokens.'
  },

  // Safety/Guard Models - Not for chatting
  {
    value: 'meta-llama/llama-guard-4-12b',
    label: 'Llama Guard 4 (Safety)',
    tier: 'safety',
    rpm: 30,
    rpd: '14.4K',
    tpm: '15K',
    tpd: '500K',
    desc: 'Model safety - TIDAK untuk chatting.'
  },
  {
    value: 'openai/gpt-oss-safeguard-20b',
    label: 'GPT-OSS Safeguard (Safety)',
    tier: 'safety',
    rpm: 30,
    rpd: '1K',
    tpm: '8K',
    tpd: '200K',
    desc: 'Model safeguard - TIDAK untuk chatting.'
  },
]

// Group models by tier
const modelOptions = computed(() => {
  return groqModels.map(m => ({
    value: m.value,
    label: m.label
  }))
})

// Get selected model info
const selectedModelInfo = computed(() => {
  const modelName = settingsStore.chatbotSettings.model_name || 'llama-3.3-70b-versatile'
  return groqModels.find(m => m.value === modelName) || groqModels[1]
})

// Computed for single channel selection (syncs with enabled_channels array)
const selectedChannel = computed({
  get: () => {
    const channels = settingsStore.chatbotSettings.enabled_channels
    return channels?.[0] || ''
  },
  set: (val) => {
    if (val) {
      settingsStore.chatbotSettings.enabled_channels = [val]
    } else {
      settingsStore.chatbotSettings.enabled_channels = []
    }
  }
})

// Store original settings for change detection
const originalSettings = ref('')

// Check if there are unsaved changes
const hasUnsavedChanges = computed(() => {
  if (!originalSettings.value) return false
  const currentSettings = JSON.stringify(settingsStore.chatbotSettings)
  return currentSettings !== originalSettings.value
})

// Reset original settings after save
function resetOriginalSettings() {
  originalSettings.value = JSON.stringify(settingsStore.chatbotSettings)
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
    settingsStore.loadChatbotSettings(guildId.value),
    guildStore.loadChannels(guildId.value)
  ])
  // Set original settings after loading
  originalSettings.value = JSON.stringify(settingsStore.chatbotSettings)
}

async function saveSettings() {
  const success = await settingsStore.saveChatbotSettings(guildId.value)
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
        <div class="w-10 h-10 bg-gradient-to-br from-discord-blurple to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/>
          </svg>
        </div>
        <div>
          <h2 class="text-xl font-bold text-white">AI Chatbot</h2>
          <p class="text-discord-text-secondary text-sm">Configure the AI chatbot settings</p>
        </div>
      </div>
    </div>

    <!-- Enable Chatbot -->
    <Card>
      <template #title>
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-discord-green" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
          </svg>
          <span>Power</span>
        </div>
      </template>
      <Toggle
        v-model="settingsStore.chatbotSettings.enabled"
        label="Enable Chatbot"
        description="Allow the bot to respond to messages using AI"
      />
    </Card>

    <!-- Channel & API Configuration Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Channel Selection -->
      <Card>
        <template #title>
          <div class="flex items-center gap-2">
            <svg class="w-5 h-5 text-discord-blurple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14"/>
            </svg>
            <span>Channel</span>
          </div>
        </template>
        <p class="text-discord-text-secondary text-sm mb-4">
          Pilih channel di mana chatbot akan merespon pesan
        </p>
        <Select
          v-model="selectedChannel"
          label="Chatbot Channel"
          placeholder="Pilih channel"
          :options="channelOptions"
        />
        <p class="text-xs text-discord-text-tertiary mt-2">
          Chatbot hanya akan merespon pesan di channel yang dipilih.
        </p>
      </Card>

      <!-- API Key Configuration -->
      <Card>
        <template #title>
          <div class="flex items-center gap-2">
            <svg class="w-5 h-5 text-discord-yellow" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"/>
            </svg>
            <span>API Key (Groq)</span>
          </div>
        </template>
        <Input
          v-model="settingsStore.chatbotSettings.api_key"
          type="password"
          label="Groq API Key"
          placeholder="gsk_..."
        />
        <p class="text-xs text-discord-text-tertiary mt-2">
          Dapatkan API key di
          <a
            href="https://console.groq.com/keys"
            target="_blank"
            rel="noopener noreferrer"
            class="text-discord-blurple hover:underline"
          >
            console.groq.com/keys
          </a>
        </p>
      </Card>
    </div>

    <!-- Model Configuration -->
    <Card>
      <template #title>
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
          </svg>
          <span>Model Configuration</span>
        </div>
      </template>
      <div class="space-y-4">
        <Select
          v-model="settingsStore.chatbotSettings.model_name"
          label="Pilih Model AI"
          placeholder="Pilih model..."
          :options="modelOptions"
        />

        <!-- Model Info Card -->
        <div
          v-if="selectedModelInfo"
          class="p-4 rounded-lg border"
          :class="{
            'border-green-500/50 bg-green-500/10': selectedModelInfo.tier === 'recommended',
            'border-yellow-500/50 bg-yellow-500/10': selectedModelInfo.tier === 'good',
            'border-gray-500/50 bg-gray-500/10': selectedModelInfo.tier === 'other',
            'border-red-500/50 bg-red-500/10': selectedModelInfo.tier === 'safety',
            'border-purple-500/50 bg-purple-500/10': selectedModelInfo.tier === 'vision',
            'border-orange-500/50 bg-orange-500/10': selectedModelInfo.tier === 'reasoning'
          }"
        >
          <div class="flex items-start gap-3">
            <!-- Tier indicator with colored dot -->
            <span class="flex-shrink-0 w-6 h-6 flex items-center justify-center">
              <span v-if="selectedModelInfo.tier === 'recommended'" class="w-3 h-3 rounded-full bg-green-500"></span>
              <span v-else-if="selectedModelInfo.tier === 'good'" class="w-3 h-3 rounded-full bg-yellow-500"></span>
              <span v-else-if="selectedModelInfo.tier === 'safety'">
                <svg class="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
                </svg>
              </span>
              <span v-else-if="selectedModelInfo.tier === 'vision'">
                <svg class="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                </svg>
              </span>
              <span v-else-if="selectedModelInfo.tier === 'reasoning'">
                <svg class="w-5 h-5 text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                </svg>
              </span>
              <span v-else class="w-3 h-3 rounded-full bg-gray-500"></span>
            </span>
            <div class="flex-1">
              <p class="text-white font-medium">{{ selectedModelInfo.desc }}</p>
              <div class="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-sm text-discord-text-secondary">
                <span class="flex items-center gap-1">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
                  </svg>
                  {{ selectedModelInfo.rpm }} req/min
                </span>
                <span class="flex items-center gap-1">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
                  </svg>
                  {{ selectedModelInfo.rpd }} req/day
                </span>
                <span class="flex items-center gap-1">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"/>
                  </svg>
                  {{ selectedModelInfo.tpm }} toks/min
                </span>
                <span class="flex items-center gap-1">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"/>
                  </svg>
                  {{ selectedModelInfo.tpd }} toks/day
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Advanced Settings -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4 border-t border-discord-bg-tertiary">
          <div>
            <div class="flex items-center gap-1 mb-2">
              <label class="text-sm font-medium text-discord-text-secondary">Max History Messages</label>
              <div class="group relative">
                <span class="text-discord-text-tertiary cursor-help border border-discord-text-tertiary rounded-full w-3.5 h-3.5 flex items-center justify-center text-[10px]">?</span>
                <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 p-2 bg-black text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity w-48 text-center pointer-events-none z-10 shadow-lg">
                  Jumlah pesan sebelumnya yang diingat AI dalam percakapan. Lebih tinggi = konteks lebih banyak.
                </div>
              </div>
            </div>
            <Input
              v-model.number="settingsStore.chatbotSettings.max_history"
              type="number"
              :min="1"
              :max="50"
            />
          </div>
          <div>
            <div class="flex items-center gap-1 mb-2">
              <label class="text-sm font-medium text-discord-text-secondary">Temperature (0.0 - 1.0)</label>
              <div class="group relative">
                <span class="text-discord-text-tertiary cursor-help border border-discord-text-tertiary rounded-full w-3.5 h-3.5 flex items-center justify-center text-[10px]">?</span>
                <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 p-2 bg-black text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity w-48 text-center pointer-events-none z-10 shadow-lg">
                  Kreativitas AI. 0 = sangat konsisten, 1 = lebih kreatif/random.
                </div>
              </div>
            </div>
            <Input
              v-model.number="settingsStore.chatbotSettings.temperature"
              type="number"
              :min="0"
              :max="1"
              :step="0.1"
            />
          </div>
        </div>
      </div>
    </Card>

    <!-- System Prompt -->
    <Card>
      <template #title>
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-discord-green" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
          </svg>
          <span>Personalisasi AI</span>
        </div>
      </template>
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-discord-text-secondary mb-2">Custom Instructions</label>
          <textarea
            v-model="settingsStore.chatbotSettings.system_prompt"
            class="w-full min-h-[120px] resize-y bg-discord-bg-secondary border border-discord-bg-tertiary rounded-lg px-4 py-3 text-white placeholder-discord-text-tertiary focus:outline-none focus:ring-2 focus:ring-discord-blurple focus:border-transparent transition-all"
            placeholder="Masukkan custom instructions untuk AI..."
          ></textarea>
        </div>
        <div class="flex items-start gap-2 text-sm">
          <span v-if="settingsStore.chatbotSettings.system_prompt" class="text-discord-green flex items-center gap-1">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
            </svg>
            Custom instructions aktif
          </span>
          <span v-else class="text-discord-text-tertiary flex items-center gap-1">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            Kosong = AI menggunakan perilaku default
          </span>
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
