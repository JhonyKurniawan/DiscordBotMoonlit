<script setup>
defineProps({
  modelValue: [String, Number],
  type: {
    type: String,
    default: 'text'
  },
  label: String,
  placeholder: String,
  min: Number,
  max: Number,
  step: Number,
  disabled: Boolean
})

defineEmits(['update:modelValue'])
</script>

<template>
  <div>
    <label v-if="label" class="block text-sm font-medium text-discord-text-secondary mb-2">{{ label }}</label>
    <input
      :type="type"
      :value="modelValue"
      @input="$emit('update:modelValue', $event.target.value)"
      :placeholder="placeholder"
      :min="min"
      :max="max"
      :step="step"
      :disabled="disabled"
      :class="['input', type === 'color' && 'input-color']"
    />
  </div>
</template>

<style scoped>
.input {
  width: 100%;
  padding: 0.625rem 0.75rem;
  background: #383a40;
  border: 1px solid #1e1f22;
  border-radius: 0.375rem;
  color: #dbdee1;
  font-size: 0.875rem;
  transition: all 0.15s ease;
}

.input:hover {
  background: #404249;
  border-color: #4e5058;
}

.input:focus {
  outline: none;
  border-color: #5865f2;
  background: #404249;
}

.input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.input[type="number"] {
  -moz-appearance: textfield;
}

.input[type="number"]::-webkit-inner-spin-button,
.input[type="number"]::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.input-color {
  height: 40px;
  padding: 0.25rem;
  cursor: pointer;
}

.input-color::-webkit-color-swatch-wrapper {
  padding: 0;
}

.input-color::-webkit-color-swatch {
  border: none;
  border-radius: 0.25rem;
}

.input[type="range"] {
  padding: 0;
  height: 6px;
  background: #404249;
  border-radius: 3px;
  appearance: none;
  -webkit-appearance: none;
}

.input[type="range"]::-webkit-slider-thumb {
  appearance: none;
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  background: #5865f2;
  border-radius: 50%;
  cursor: pointer;
  transition: background 0.15s ease;
}

.input[type="range"]::-webkit-slider-thumb:hover {
  background: #4752c4;
}

.input[type="range"]::-moz-range-thumb {
  width: 16px;
  height: 16px;
  background: #5865f2;
  border: none;
  border-radius: 50%;
  cursor: pointer;
}
</style>
