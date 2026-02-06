<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: Number,
    required: true
  },
  label: String,
  min: {
    type: Number,
    default: 0
  },
  max: {
    type: Number,
    default: 100
  },
  step: {
    type: Number,
    default: 1
  },
  default: {
    type: Number,
    required: true
  },
  unit: {
    type: String,
    default: 'px'
  }
})

const emit = defineEmits(['update:modelValue', 'reset'])

const localValue = ref(props.modelValue)

// Sync local value with props
watch(() => props.modelValue, (newValue) => {
  localValue.value = newValue
})

// When user types in input, emit update
watch(localValue, (newValue) => {
  const numValue = Number(newValue)
  if (!isNaN(numValue) && numValue >= props.min && numValue <= props.max) {
    emit('update:modelValue', numValue)
  }
})

function handleSliderInput(event) {
  const value = Number(event.target.value)
  localValue.value = value
  emit('update:modelValue', value)
}

function handleReset() {
  localValue.value = props.default
  emit('reset', props.default)
}
</script>

<template>
  <div class="range-input-wrapper">
    <label v-if="label" class="range-label">
      <span class="label-text">{{ label }}</span>
      <input
        :value="localValue"
        @input="localValue = $event.target.value"
        @blur="localValue = Math.max(props.min, Math.min(props.max, Number(localValue) || props.default))"
        type="number"
        :min="min"
        :max="max"
        class="size-input"
      />
      <span class="unit-text">{{ unit }}</span>
    </label>
    <div class="flex items-center gap-2">
      <div class="flex-1 relative">
        <input
          :value="modelValue"
          @input="handleSliderInput"
          type="range"
          :min="min"
          :max="max"
          :step="step"
          class="input-range"
        />
      </div>
      <button
        @click="handleReset"
        class="reset-btn"
        :title="`Reset to ${props.default}${unit}`"
        :class="{ 'is-reset': modelValue === props.default }"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74-2.74L3 8"/>
          <path d="M3 3v5h5"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.range-input-wrapper {
  width: 100%;
}

.range-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #b5bac1;
  margin-bottom: 0.375rem;
}

.label-text {
  flex-shrink: 0;
}

.size-input {
  width: 60px;
  padding: 0.25rem 0.5rem;
  background: #383a40;
  border: 1px solid #1e1f22;
  border-radius: 0.25rem;
  color: #dbdee1;
  font-size: 0.875rem;
  text-align: center;
}

.size-input:focus {
  outline: none;
  border-color: #5865f2;
}

.unit-text {
  color: #80848e;
  font-size: 0.75rem;
}

.input-range {
  width: 100%;
  height: 6px;
  background: #404249;
  border-radius: 3px;
  appearance: none;
  -webkit-appearance: none;
  padding: 0;
  cursor: pointer;
}

.input-range::-webkit-slider-thumb {
  appearance: none;
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  background: #5865f2;
  border-radius: 50%;
  cursor: pointer;
  transition: background 0.15s ease;
}

.input-range::-webkit-slider-thumb:hover {
  background: #4752c4;
}

.input-range::-moz-range-thumb {
  width: 16px;
  height: 16px;
  background: #5865f2;
  border: none;
  border-radius: 50%;
  cursor: pointer;
}

.reset-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.375rem;
  background: #404249;
  border: none;
  border-radius: 0.25rem;
  color: #dbdee1;
  cursor: pointer;
  transition: background 0.15s ease;
  flex-shrink: 0;
}

.reset-btn:hover {
  background: #4e5058;
}

.reset-btn.is-reset {
  opacity: 0.5;
}

.reset-btn svg {
  width: 14px;
  height: 14px;
}
</style>
