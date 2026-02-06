<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: '#000000'
  },
  label: String,
  placeholder: String,
  disabled: Boolean
})

const emit = defineEmits(['update:modelValue'])

const inputValue = computed({
  get: () => props.modelValue,
  set: (value) => {
    // Basic validation/formatting could go here
    emit('update:modelValue', value)
  }
})

function handleTextInput(event) {
  let value = event.target.value
  // Auto-prepend # if missing and it looks like a hex code
  if (value && !value.startsWith('#') && /^[0-9A-Fa-f]{0,6}$/.test(value)) {
    value = '#' + value
  }
  emit('update:modelValue', value)
}
</script>

<template>
  <div>
    <label v-if="label" class="block text-sm font-medium text-discord-text-secondary mb-2">{{ label }}</label>
    <div class="relative flex items-center">
      <!-- Color Preview / Picker Trigger -->
      <div class="absolute left-2 top-1/2 -translate-y-1/2 w-6 h-6 rounded border border-discord-bg-tertiary overflow-hidden cursor-pointer shadow-sm">
        <input
          type="color"
          :value="modelValue"
          @input="$emit('update:modelValue', $event.target.value)"
          :disabled="disabled"
          class="absolute -top-1/2 -left-1/2 w-[200%] h-[200%] p-0 m-0 border-0 cursor-pointer opacity-0"
        />
        <div 
          class="w-full h-full pointer-events-none"
          :style="{ backgroundColor: modelValue }"
        ></div>
      </div>

      <!-- Hex Input -->
      <input
        type="text"
        :value="modelValue"
        @input="handleTextInput"
        :placeholder="placeholder || '#000000'"
        :disabled="disabled"
        class="w-full pl-10 pr-3 py-2.5 bg-discord-bg-secondary border border-discord-bg-primary rounded-md text-discord-text-primary text-sm focus:outline-none focus:border-discord-blurple focus:bg-discord-bg-tertiary transition-colors font-mono"
        spellcheck="false"
      />
    </div>
  </div>
</template>
