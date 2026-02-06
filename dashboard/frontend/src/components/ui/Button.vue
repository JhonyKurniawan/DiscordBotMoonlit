<script setup>
defineProps({
  variant: {
    type: String,
    default: 'primary',
    validator: (value) => ['primary', 'secondary', 'danger', 'success', 'ghost', 'outline'].includes(value)
  },
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md', 'lg'].includes(value)
  },
  disabled: Boolean,
  loading: Boolean,
  icon: Boolean,
  type: {
    type: String,
    default: 'button'
  }
})

defineEmits(['click'])
</script>

<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    @click="$emit('click')"
    class="relative inline-flex items-center justify-center gap-2 font-semibold rounded-xl transition-all duration-200 ease-out focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-discord-bg-primary disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none overflow-hidden group"
    :class="[
      // Size variants
      size === 'sm' && 'px-3.5 py-2 text-xs rounded-lg',
      size === 'md' && 'px-5 py-2.5 text-sm rounded-xl',
      size === 'lg' && 'px-7 py-3.5 text-base rounded-xl',
      icon && size === 'sm' && '!px-2',
      icon && size === 'md' && '!px-3',
      icon && size === 'lg' && '!px-4',
      
      // Primary - Blurple gradient with glow
      variant === 'primary' && 'bg-gradient-to-r from-discord-blurple to-indigo-500 text-white shadow-lg shadow-discord-blurple/25 hover:shadow-xl hover:shadow-discord-blurple/40 hover:scale-[1.02] active:scale-[0.98] focus:ring-discord-blurple',
      
      // Secondary - Subtle dark background
      variant === 'secondary' && 'bg-discord-bg-tertiary text-discord-text-primary hover:bg-discord-bg-hover hover:text-white active:scale-[0.98] focus:ring-discord-bg-tertiary',
      
      // Danger - Red gradient with glow
      variant === 'danger' && 'bg-gradient-to-r from-discord-red to-red-600 text-white shadow-lg shadow-discord-red/25 hover:shadow-xl hover:shadow-discord-red/40 hover:scale-[1.02] active:scale-[0.98] focus:ring-discord-red',
      
      // Success - Green gradient with glow
      variant === 'success' && 'bg-gradient-to-r from-discord-green to-emerald-500 text-white shadow-lg shadow-discord-green/25 hover:shadow-xl hover:shadow-discord-green/40 hover:scale-[1.02] active:scale-[0.98] focus:ring-discord-green',
      
      // Ghost - Transparent with hover effect
      variant === 'ghost' && 'bg-transparent text-discord-text-secondary hover:bg-discord-bg-tertiary hover:text-white active:scale-[0.98] focus:ring-discord-bg-tertiary',
      
      // Outline - Border only
      variant === 'outline' && 'bg-transparent border-2 border-discord-blurple text-discord-blurple hover:bg-discord-blurple hover:text-white active:scale-[0.98] focus:ring-discord-blurple'
    ]"
  >
    <!-- Shine effect overlay -->
    <span 
      v-if="variant === 'primary' || variant === 'danger' || variant === 'success'"
      class="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700 ease-in-out"
    ></span>
    
    <!-- Loading spinner -->
    <svg 
      v-if="loading" 
      class="animate-spin h-4 w-4" 
      :class="size === 'lg' && 'h-5 w-5'"
      fill="none" 
      viewBox="0 0 24 24"
    >
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
    </svg>
    
    <!-- Button content -->
    <span class="relative z-10 flex items-center gap-2" :class="loading && 'opacity-0'">
      <slot />
    </span>
  </button>
</template>
