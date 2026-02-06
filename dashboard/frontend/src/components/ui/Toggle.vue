<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: [Boolean, Number],
    default: false
  },
  label: String,
  description: String
})

const emit = defineEmits(['update:modelValue'])

const isActive = computed({
  get: () => Boolean(props.modelValue),
  set: (value) => emit('update:modelValue', value)
})

function toggle() {
  isActive.value = !isActive.value
}
</script>

<template>
  <div class="flex items-center justify-between">
    <div>
      <label v-if="label" class="block text-discord-text-primary font-medium">{{ label }}</label>
      <p v-if="description" class="text-sm text-discord-text-secondary mt-1">{{ description }}</p>
    </div>
    <button
      @click="toggle"
      class="toggle-switch"
      :class="{ active: isActive }"
      type="button"
    >
      <input type="checkbox" :checked="isActive" class="hidden" />
    </button>
  </div>
</template>
