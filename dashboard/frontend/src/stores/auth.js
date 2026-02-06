import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/services/api'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref(null)
  const token = ref(localStorage.getItem('discord_token') || null)
  const loading = ref(false)

  // Getters
  const isLoggedIn = computed(() => !!token.value && !!user.value)
  const userInitial = computed(() => user.value?.username?.charAt(0)?.toUpperCase() || '?')
  const userAvatar = computed(() => {
    if (!user.value) return null
    if (user.value.avatar) {
      return `https://cdn.discordapp.com/avatars/${user.value.id}/${user.value.avatar}.png`
    }
    // Return default avatar based on discriminator
    const disc = user.value.discriminator || '0'
    if (disc === '0') {
      return `https://cdn.discordapp.com/embed/avatars/${parseInt(user.value.id) % 5}.png`
    }
    return `https://cdn.discordapp.com/embed/avatars/${(parseInt(disc) % 5)}.png`
  })

  // Actions
  async function checkAuth() {
    if (!token.value) {
      return false
    }

    loading.value = true
    try {
      const response = await authApi.getMe()
      if (response.data && !response.data.error) {
        user.value = response.data
        return true
      }
      return false
    } catch (error) {
      console.error('Auth check failed:', error)
      logout()
      return false
    } finally {
      loading.value = false
    }
  }

  function setUser(userData) {
    user.value = userData
    if (userData) {
      localStorage.setItem('discord_user', JSON.stringify(userData))
    } else {
      localStorage.removeItem('discord_user')
    }
  }

  function setToken(tokenValue) {
    token.value = tokenValue
    if (tokenValue) {
      localStorage.setItem('discord_token', tokenValue)
    } else {
      localStorage.removeItem('discord_token')
    }
  }

  async function logout() {
    try {
      await authApi.logout()
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      user.value = null
      token.value = null
      localStorage.removeItem('discord_token')
      localStorage.removeItem('discord_user')
    }
  }

  function initFromStorage() {
    const storedUser = localStorage.getItem('discord_user')
    if (storedUser) {
      try {
        user.value = JSON.parse(storedUser)
      } catch (error) {
        console.error('Failed to parse stored user:', error)
      }
    }
  }

  return {
    user,
    token,
    loading,
    isLoggedIn,
    userInitial,
    userAvatar,
    checkAuth,
    setUser,
    setToken,
    logout,
    initFromStorage
  }
})
