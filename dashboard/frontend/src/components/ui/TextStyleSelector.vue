<script setup>
defineProps({
  bold: Boolean,
  italic: Boolean,
  underline: Boolean,
  label: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:bold', 'update:italic', 'update:underline'])
</script>

<template>
  <div class="space-y-2">
    <label v-if="label" class="block text-xs font-semibold text-discord-text-secondary uppercase">
      {{ label }}
    </label>
    <div class="flex items-center gap-1 bg-discord-bg-tertiary p-1 rounded-lg w-fit">
      <!-- Bold -->
      <button
        @click="emit('update:bold', !bold)"
        class="p-2 rounded md:hover:bg-discord-bg-primary transition-colors focus:outline-none"
        :class="bold ? 'bg-discord-blurple text-white md:hover:bg-discord-blurple' : 'text-discord-text-secondary hover:text-discord-text-primary'"
        title="Bold"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 4h8a4 4 0 014 4 4 4 0 01-4 4H6V4zm0 8h9a4 4 0 014 4 4 4 0 01-4 4H6v-8z"/>
        </svg>
      </button>

      <!-- Italic -->
      <button
        @click="emit('update:italic', !italic)"
        class="p-2 rounded md:hover:bg-discord-bg-primary transition-colors focus:outline-none"
        :class="italic ? 'bg-discord-blurple text-white md:hover:bg-discord-blurple' : 'text-discord-text-secondary hover:text-discord-text-primary'"
        title="Italic"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M10 4h4m-2 0v16m-2 0h4m-6-8h0"/> <!-- Custom path for Italic usually just a slanted line or serif-I -->
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 4h-9m4 16h5M14 4l-4 16"/>
        </svg>
      </button>

      <!-- Underline -->
      <button
        @click="emit('update:underline', !underline)"
        class="p-2 rounded md:hover:bg-discord-bg-primary transition-colors focus:outline-none"
        :class="underline ? 'bg-discord-blurple text-white md:hover:bg-discord-blurple' : 'text-discord-text-secondary hover:text-discord-text-primary'"
        title="Underline"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 4v7a6 6 0 0012 0V4M4 21h16"/>
        </svg>
      </button>
    </div>
  </div>
</template>
