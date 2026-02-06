<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { RouterView } from 'vue-router'
import StatusMessage from '@/components/ui/StatusMessage.vue'

const authStore = useAuthStore()

onMounted(() => {
  authStore.initFromStorage()
})
</script>

<template>
  <RouterView />
  <StatusMessage />
</template>
