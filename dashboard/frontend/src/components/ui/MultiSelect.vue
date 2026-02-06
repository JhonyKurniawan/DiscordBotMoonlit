<script setup>
import { ref, computed, onUnmounted } from 'vue'

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  },
  options: {
    type: Array,
    default: () => []
  },
  label: String,
  placeholder: {
    type: String,
    default: 'Select options'
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const isOpen = ref(false)
const selectEl = ref(null)

const selectedOptions = computed(() => {
  return props.options.filter(opt => props.modelValue.includes(String(opt.value)))
})

const displayText = computed(() => {
  if (selectedOptions.value.length === 0) return props.placeholder
  if (selectedOptions.value.length === 1) return selectedOptions.value[0].label
  return `${selectedOptions.value.length} dipilih`
})

function toggleOption(option) {
  const newValue = [...props.modelValue]
  const valueStr = String(option.value)
  const index = newValue.indexOf(valueStr)
  if (index > -1) {
    newValue.splice(index, 1)
  } else {
    newValue.push(valueStr)
  }
  emit('update:modelValue', newValue)
}

function isSelected(option) {
  return props.modelValue.includes(String(option.value))
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
  <div class="multiselect-wrapper" ref="selectEl">
    <label v-if="label" class="multiselect-label">{{ label }}</label>
    <div class="multiselect-container">
      <button
        type="button"
        class="multiselect-button"
        :class="{ disabled, open: isOpen }"
        :disabled="disabled"
        @click="toggleOpen"
      >
        <span class="multiselect-value">{{ displayText }}</span>
        <svg class="multiselect-arrow" :class="{ open: isOpen }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
        </svg>
      </button>
      <Transition name="dropdown">
        <div v-if="isOpen && options.length > 0" class="multiselect-dropdown">
          <div
            v-for="option in options"
            :key="option.value"
            class="multiselect-option"
            :class="{ selected: isSelected(option) }"
            @click="toggleOption(option)"
          >
            <span v-if="option.color" class="role-dot" :style="{ backgroundColor: '#' + option.color.toString(16).padStart(6, '0') }"></span>
            <span class="multiselect-option-text">{{ option.label }}</span>
            <span v-if="isSelected(option)" class="checkmark">✓</span>
          </div>
        </div>
        <div v-else-if="isOpen && options.length === 0" class="multiselect-dropdown">
          <div class="multiselect-option disabled">Tidak ada role tersedia</div>
        </div>
      </Transition>
    </div>
  </div>
</template>

<style scoped>
.multiselect-wrapper {
  width: 100%;
}

.multiselect-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: #b5bac1;
  margin-bottom: 0.375rem;
}

.multiselect-container {
  position: relative;
  width: 100%;
}

.multiselect-button {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.625rem 0.75rem;
  background: #383a40;
  border: 1px solid #1e1f22;
  border-radius: 0.375rem;
  color: #dbdee1;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.15s ease;
  text-align: left;
}

.multiselect-button:hover:not(.disabled) {
  background: #404249;
  border-color: #4e5058;
}

.multiselect-button.open {
  border-color: #5865f2;
  background: #404249;
}

.multiselect-button.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.multiselect-value {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.multiselect-arrow {
  width: 1rem;
  height: 1rem;
  flex-shrink: 0;
  transition: transform 0.15s ease;
  color: #b5bac1;
}

.multiselect-arrow.open {
  transform: rotate(180deg);
}

.multiselect-dropdown {
  position: absolute;
  top: calc(100% + 0.25rem);
  left: 0;
  right: 0;
  background: #313338;
  border: 1px solid #1e1f22;
  border-radius: 0.375rem;
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
  max-height: 12rem;
  overflow-y: auto;
  z-index: 50;
}

.multiselect-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 0.75rem;
  font-size: 0.875rem;
  color: #dbdee1;
  cursor: pointer;
  transition: background 0.1s ease;
}

.multiselect-option:hover:not(.disabled) {
  background: #404249;
}

.multiselect-option.selected {
  background: rgba(88, 101, 242, 0.2);
  color: white;
}

.multiselect-option.disabled {
  color: #80848e;
  cursor: default;
}

.multiselect-option-text {
  flex: 1;
}

.checkmark {
  color: #5865f2;
  font-weight: bold;
}

.role-dot {
  display: inline-block;
  width: 0.75rem;
  height: 0.75rem;
  border-radius: 50%;
  flex-shrink: 0;
}

/* Dropdown transition */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 0.15s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* Scrollbar styling for dropdown */
.multiselect-dropdown::-webkit-scrollbar {
  width: 0.5rem;
}

.multiselect-dropdown::-webkit-scrollbar-track {
  background: #2b2d31;
}

.multiselect-dropdown::-webkit-scrollbar-thumb {
  background: #1e1f22;
  border-radius: 0.25rem;
}
</style>
