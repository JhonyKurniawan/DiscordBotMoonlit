<script setup>
import { ref, computed, onUnmounted } from 'vue'

const props = defineProps({
  modelValue: {
    type: [String, Number],
    default: ''
  },
  options: {
    type: Array,
    default: () => []
  },
  label: String,
  placeholder: {
    type: String,
    default: 'Select an option'
  },
  disabled: {
    type: Boolean,
    default: false
  },
  fontPreview: {
    type: Boolean,
    default: false
  },
  grouped: {
    type: Boolean,
    default: false
  }
})

// Font mapping for preview
const getFontFamily = (value) => {
  const fontMap = {
    'arial': 'Arial, sans-serif',
    'impact': 'Impact, sans-serif',
    'verdana': 'Verdana, sans-serif',
    'comic': '"Comic Sans MS", cursive, sans-serif',
    'georgia': 'Georgia, serif',
    'times': '"Times New Roman", Times, serif'
  }
  return fontMap[value] || 'inherit'
}

const emit = defineEmits(['update:modelValue'])

const isOpen = ref(false)
const selectEl = ref(null)

const selectedOption = computed(() => {
  return props.options.find(opt => String(opt.value) === String(props.modelValue))
})

const groupedOptions = computed(() => {
  const groups = {}
  props.options.forEach(option => {
    const groupName = option.group || 'Other'
    if (!groups[groupName]) {
      groups[groupName] = []
    }
    groups[groupName].push(option)
  })
  return groups
})

function selectOption(option) {
  emit('update:modelValue', option.value)
  isOpen.value = false
}

function toggleOpen() {
  if (!props.disabled) {
    isOpen.value = !isOpen.value
  }
}

function closeDropdown(event) {
  if (selectEl.value && !selectEl.value.contains(event.target)) {
    isOpen.value = false
  }
}

function handleClickOutside(event) {
  closeDropdown(event)
}

// Add click outside listener on mount
document.addEventListener('click', handleClickOutside)

// Clean up on unmount
onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <div class="select-wrapper" ref="selectEl">
    <label v-if="label" class="block text-sm font-medium text-discord-text-secondary mb-1.5">{{ label }}</label>
    <div class="relative">
      <!-- Select Button -->
      <button
        type="button"
        class="w-full flex items-center justify-between gap-2 px-4 py-2.5 bg-discord-bg-tertiary border border-discord-bg-tertiary rounded-xl text-sm cursor-pointer transition-all duration-200 text-left group"
        :class="{
          'opacity-50 cursor-not-allowed': disabled,
          'border-discord-blurple ring-2 ring-discord-blurple/20 bg-discord-bg-hover': isOpen,
          'hover:bg-discord-bg-hover hover:border-discord-bg-hover': !disabled && !isOpen
        }"
        :disabled="disabled"
        @click="toggleOpen"
      >
        <!-- Selected Value -->
        <span v-if="selectedOption" class="flex items-center gap-2 overflow-hidden text-ellipsis whitespace-nowrap text-white">
          <span v-if="selectedOption.icon" class="flex-shrink-0">{{ selectedOption.icon }}</span>
          <span 
            v-if="selectedOption.color" 
            class="w-3 h-3 rounded-full flex-shrink-0 ring-2 ring-white/20" 
            :style="{ backgroundColor: '#' + selectedOption.color.toString(16).padStart(6, '0') }"
          ></span>
          <span
            :style="{
              color: selectedOption.color ? '#' + selectedOption.color.toString(16).padStart(6, '0') : '',
              fontFamily: fontPreview ? getFontFamily(selectedOption.value) : ''
            }"
          >{{ selectedOption.label }}</span>
        </span>
        <span v-else class="text-discord-text-muted">{{ placeholder }}</span>
        
        <!-- Arrow Icon -->
        <svg 
          class="w-4 h-4 flex-shrink-0 text-discord-text-secondary transition-transform duration-200" 
          :class="{ 'rotate-180 text-discord-blurple': isOpen }"
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
        </svg>
      </button>
      
      <!-- Dropdown Menu -->
      <Transition
        enter-active-class="transition-all duration-200 ease-out"
        enter-from-class="opacity-0 -translate-y-2 scale-95"
        enter-to-class="opacity-100 translate-y-0 scale-100"
        leave-active-class="transition-all duration-150 ease-in"
        leave-from-class="opacity-100 translate-y-0 scale-100"
        leave-to-class="opacity-0 -translate-y-2 scale-95"
      >
        <div 
          v-if="isOpen && options.length > 0" 
          class="absolute top-full left-0 right-0 mt-2 bg-discord-bg-secondary border border-discord-bg-tertiary rounded-xl shadow-2xl overflow-hidden z-50 backdrop-blur-sm"
        >
          <div class="max-h-60 overflow-y-auto py-1 custom-scrollbar">
            <!-- Grouped Options -->
            <template v-if="grouped">
              <template v-for="(group, groupName) in groupedOptions" :key="groupName">
                <div class="px-3 py-2 text-xs font-semibold text-discord-text-muted uppercase tracking-wider bg-discord-bg-tertiary/50 sticky top-0">
                  {{ groupName }}
                </div>
                <div
                  v-for="option in group"
                  :key="option.value"
                  class="flex items-center gap-3 px-3 py-2.5 mx-1 rounded-lg cursor-pointer transition-all duration-150"
                  :class="{
                    'bg-discord-blurple text-white': String(option.value) === String(modelValue),
                    'text-discord-text-primary hover:bg-discord-bg-tertiary': String(option.value) !== String(modelValue)
                  }"
                  @click="selectOption(option)"
                >
                  <span v-if="option.icon" class="flex-shrink-0">{{ option.icon }}</span>
                  <span 
                    v-if="option.color" 
                    class="w-3 h-3 rounded-full flex-shrink-0" 
                    :style="{ backgroundColor: '#' + option.color.toString(16).padStart(6, '0') }"
                  ></span>
                  <span
                    class="flex-1"
                    :style="{
                      color: String(option.value) === String(modelValue) ? '' : (option.color ? '#' + option.color.toString(16).padStart(6, '0') : ''),
                      fontFamily: fontPreview ? getFontFamily(option.value) : ''
                    }"
                  >{{ option.label }}</span>
                  <!-- Checkmark -->
                  <svg 
                    v-if="String(option.value) === String(modelValue)"
                    class="w-4 h-4 flex-shrink-0" 
                    fill="none" 
                    stroke="currentColor" 
                    viewBox="0 0 24 24"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
                  </svg>
                </div>
              </template>
            </template>
            
            <!-- Regular Options -->
            <template v-else>
              <div
                v-for="option in options"
                :key="option.value"
                class="flex items-center gap-3 px-3 py-2.5 mx-1 rounded-lg cursor-pointer transition-all duration-150"
                :class="{
                  'bg-discord-blurple text-white': String(option.value) === String(modelValue),
                  'text-discord-text-primary hover:bg-discord-bg-tertiary': String(option.value) !== String(modelValue)
                }"
                @click="selectOption(option)"
              >
                <span v-if="option.icon" class="flex-shrink-0">{{ option.icon }}</span>
                <span 
                  v-if="option.color" 
                  class="w-3 h-3 rounded-full flex-shrink-0" 
                  :style="{ backgroundColor: '#' + option.color.toString(16).padStart(6, '0') }"
                ></span>
                <span
                  class="flex-1"
                  :style="{
                    color: String(option.value) === String(modelValue) ? '' : (option.color ? '#' + option.color.toString(16).padStart(6, '0') : ''),
                    fontFamily: fontPreview ? getFontFamily(option.value) : ''
                  }"
                >{{ option.label }}</span>
                <!-- Checkmark -->
                <svg 
                  v-if="String(option.value) === String(modelValue)"
                  class="w-4 h-4 flex-shrink-0" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
                </svg>
              </div>
            </template>
          </div>
        </div>
        
        <!-- Empty State -->
        <div 
          v-else-if="isOpen && options.length === 0" 
          class="absolute top-full left-0 right-0 mt-2 bg-discord-bg-secondary border border-discord-bg-tertiary rounded-xl shadow-2xl overflow-hidden z-50"
        >
          <div class="px-4 py-6 text-center text-discord-text-muted text-sm">
            <svg class="w-8 h-8 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"/>
            </svg>
            No options available
          </div>
        </div>
      </Transition>
    </div>
  </div>
</template>

<style scoped>
.select-wrapper {
  width: 100%;
}

/* Custom scrollbar for dropdown */
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #4e5058;
  border-radius: 3px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #5865f2;
}
</style>
