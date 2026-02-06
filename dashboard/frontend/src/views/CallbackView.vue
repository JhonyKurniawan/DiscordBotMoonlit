<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

onMounted(() => {
  // Router guard will handle the callback logic
  // This is just a loading state
})
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-discord-bg-primary">
    <div class="text-center">
      <div class="w-12 h-12 border-4 border-discord-blurple border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
      <p class="text-discord-text-secondary">Logging you in...</p>
    </div>
  </div>
</template>
