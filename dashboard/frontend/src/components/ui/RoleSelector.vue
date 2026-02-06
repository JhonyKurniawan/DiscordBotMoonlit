<script setup>
import { computed } from 'vue'

const props = defineProps({
  roles: {
    type: Array,
    default: () => []
  },
  selectedIds: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['toggle'])

function isSelected(roleId) {
  // Convert both to strings for safe comparison
  return props.selectedIds.map(String).includes(String(roleId))
}

function getRoleColor(role) {
  if (!role.color) return '#99AAB5' // Default discord grey
  return '#' + role.color.toString(16).padStart(6, '0')
}

// Helper to determine if a color is light or dark to adjust text color
function getContrastColor(hexcolor) {
    if (!hexcolor || hexcolor === '#99AAB5') return '#FFFFFF';
    
    // Remove # if present
    hexcolor = hexcolor.replace('#', '');
    
    // Parse r, g, b
    var r = parseInt(hexcolor.substr(0,2),16);
    var g = parseInt(hexcolor.substr(2,2),16);
    var b = parseInt(hexcolor.substr(4,2),16);
    
    // Calculate YIQ ratio
    var yiq = ((r*299)+(g*587)+(b*114))/1000;
    
    // Return black for light colors, white for dark colors
    return (yiq >= 128) ? '#000000' : '#FFFFFF';
}
</script>

<template>
  <div class="flex flex-wrap gap-2">
    <button
      v-for="role in roles"
      :key="role.value"
      @click="emit('toggle', role.value)"
      class="group relative flex items-center gap-2 px-3 py-1.5 rounded-full border transition-all duration-200 ease-in-out"
      :class="[
        isSelected(role.value) 
          ? 'bg-discord-bg-tertiary border-discord-blurple shadow-sm ring-1 ring-discord-blurple' 
          : 'bg-discord-bg-secondary border-transparent hover:border-discord-bg-tertiary hover:bg-discord-bg-tertiary'
      ]"
    >
      <!-- Color Indicator (Circle) -->
      <span 
        class="w-3 h-3 rounded-full shadow-sm"
        :style="{ backgroundColor:getRoleColor(role) }"
      ></span>
      
      <!-- Role Name -->
      <span 
        class="text-sm font-medium transition-colors"
        :class="isSelected(role.value) ? 'text-white' : 'text-discord-text-secondary group-hover:text-discord-text-primary'"
      >
        {{ role.label }}
      </span>

      <!-- Active Indicator (Optional checkmark) -->
      <Transition
        enter-active-class="transition-all duration-200 ease-out"
        enter-from-class="opacity-0 scale-50"
        enter-to-class="opacity-100 scale-100"
        leave-active-class="transition-all duration-150 ease-in"
        leave-from-class="opacity-100 scale-100"
        leave-to-class="opacity-0 scale-50"
      >
        <svg 
          v-if="isSelected(role.value)"
          class="w-3.5 h-3.5 text-discord-blurple ml-0.5" 
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
        </svg>
      </Transition>
    </button>
  </div>
</template>
