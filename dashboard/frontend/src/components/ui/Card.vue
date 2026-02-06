<script setup>
defineProps({
  title: String,
  noPadding: Boolean
})
</script>

<template>
  <div class="card" :class="{ 'p-0': noPadding }">
    <div v-if="$slots.title || title" class="flex items-center gap-2 mb-4">
      <slot name="title">
        <h3 class="text-lg font-semibold">{{ title }}</h3>
      </slot>
    </div>
    <slot />
  </div>
</template>
