import { defineStore } from 'pinia'
import { ref } from 'vue'
import { settingsApi } from '@/services/api'

export const useSettingsStore = defineStore('settings', () => {
  // State
  const guildSettings = ref({})
  const chatbotSettings = ref({})
  const levelingSettings = ref({})
  const levelRoles = ref([])
  const excludedRoles = ref([])
  const leaderboard = ref([])
  const moderationRoles = ref([])
  const moderationLogs = ref([])
  const welcomeRoles = ref([])
  const userMusicGenres = ref([])

  const loading = ref(false)
  const statusMessage = ref('')
  const statusType = ref('success') // 'success' or 'error'

  // Actions
  function showStatus(message, type = 'success') {
    statusMessage.value = message
    statusType.value = type
    setTimeout(() => {
      statusMessage.value = ''
    }, 3000)
  }

  // Guild Settings
  async function loadGuildSettings(guildId) {
    loading.value = true
    try {
      const response = await settingsApi.getGuildSettings(guildId)
      guildSettings.value = response.data || {}
      console.log('[Settings] Loaded guild settings:', guildSettings.value)
      return guildSettings.value
    } catch (error) {
      console.error('Failed to load guild settings:', error)
      return {}
    } finally {
      loading.value = false
    }
  }

  async function saveGuildSettings(guildId) {
    try {
      console.log('[Settings] Saving guild settings:', guildSettings.value)
      const response = await settingsApi.updateGuildSettings(guildId, guildSettings.value)
      console.log('[Settings] Save response:', response.data)
      showStatus('Settings saved successfully!')
      return true
    } catch (error) {
      console.error('Failed to save guild settings:', error)
      showStatus('Failed to save settings', 'error')
      return false
    }
  }

  // Chatbot Settings
  async function loadChatbotSettings(guildId) {
    loading.value = true
    try {
      const response = await settingsApi.getChatbotSettings(guildId)
      chatbotSettings.value = response.data || {}
      // Ensure enabled_channels is always an array
      if (!Array.isArray(chatbotSettings.value.enabled_channels)) {
        chatbotSettings.value.enabled_channels = []
      }
      // Ensure system_prompt is a string (handle null/undefined)
      if (chatbotSettings.value.system_prompt === null || chatbotSettings.value.system_prompt === undefined) {
        chatbotSettings.value.system_prompt = ''
      }
      console.log('[DEBUG] Loaded chatbot settings:', chatbotSettings.value)
      return chatbotSettings.value
    } catch (error) {
      console.error('Failed to load chatbot settings:', error)
      return {}
    } finally {
      loading.value = false
    }
  }

  async function saveChatbotSettings(guildId) {
    try {
      // Ensure system_prompt is properly trimmed before saving
      const dataToSave = { ...chatbotSettings.value }
      if (dataToSave.system_prompt) {
        dataToSave.system_prompt = dataToSave.system_prompt.trim()
      } else {
        dataToSave.system_prompt = ''
      }
      console.log('[DEBUG] Saving chatbot settings:', dataToSave)
      await settingsApi.updateChatbotSettings(guildId, dataToSave)
      showStatus('Chatbot settings saved!')
      return true
    } catch (error) {
      console.error('Failed to save chatbot settings:', error)
      showStatus('Failed to save chatbot settings', 'error')
      return false
    }
  }

  // Leveling Settings
  async function loadLevelingSettings(guildId) {
    loading.value = true
    try {
      const response = await settingsApi.getLevelingSettings(guildId)
      levelingSettings.value = response.data || {}
      return levelingSettings.value
    } catch (error) {
      console.error('Failed to load leveling settings:', error)
      return {}
    } finally {
      loading.value = false
    }
  }

  async function saveLevelingSettings(guildId) {
    try {
      await settingsApi.updateLevelingSettings(guildId, levelingSettings.value)
      showStatus('Leveling settings saved!')
      return true
    } catch (error) {
      console.error('Failed to save leveling settings:', error)
      showStatus('Failed to save leveling settings', 'error')
      return false
    }
  }

  async function toggleLeveling(guildId, enabled) {
    try {
      await settingsApi.toggleLeveling(guildId, enabled)
      levelingSettings.value.enabled = enabled
      showStatus(`Leveling ${enabled ? 'enabled' : 'disabled'}!`)
      return true
    } catch (error) {
      console.error('Failed to toggle leveling:', error)
      showStatus('Failed to toggle leveling', 'error')
      return false
    }
  }

  // Level Roles
  async function loadLevelRoles(guildId) {
    try {
      const response = await settingsApi.getLevelRoles(guildId)
      levelRoles.value = response.data || []
      return levelRoles.value
    } catch (error) {
      console.error('Failed to load level roles:', error)
      return []
    }
  }

  async function addLevelRole(guildId, level, roleId, stack = false) {
    try {
      await settingsApi.addLevelRole(guildId, { level, role_id: roleId, stack })
      await loadLevelRoles(guildId)
      showStatus('Level role added!')
      return true
    } catch (error) {
      console.error('Failed to add level role:', error)
      showStatus('Failed to add level role', 'error')
      return false
    }
  }

  async function removeLevelRole(guildId, level, roleId) {
    try {
      await settingsApi.removeLevelRole(guildId, { level, role_id: roleId })
      await loadLevelRoles(guildId)
      showStatus('Level role removed!')
      return true
    } catch (error) {
      console.error('Failed to remove level role:', error)
      showStatus('Failed to remove level role', 'error')
      return false
    }
  }

  async function updateLevelRole(guildId, oldLevel, oldRoleId, level, roleId, stack = false) {
    try {
      await settingsApi.updateLevelRole(guildId, { old_level: oldLevel, old_role_id: oldRoleId, level, role_id: roleId, stack })
      await loadLevelRoles(guildId)
      showStatus('Level role updated!')
      return true
    } catch (error) {
      console.error('Failed to update level role:', error)
      showStatus('Failed to update level role', 'error')
      return false
    }
  }

  // Excluded Roles
  async function loadExcludedRoles(guildId) {
    try {
      const response = await settingsApi.getExcludedRoles(guildId)
      excludedRoles.value = response.data?.data || []
      return excludedRoles.value
    } catch (error) {
      console.error('Failed to load excluded roles:', error)
      return []
    }
  }

  async function addExcludedRole(guildId, roleId) {
    try {
      await settingsApi.addExcludedRole(guildId, { role_id: roleId })
      await loadExcludedRoles(guildId)
      showStatus('Role excluded from XP!')
      return true
    } catch (error) {
      console.error('Failed to add excluded role:', error)
      showStatus('Failed to add excluded role', 'error')
      return false
    }
  }

  async function removeExcludedRole(guildId, roleId) {
    try {
      await settingsApi.removeExcludedRole(guildId, { role_id: roleId })
      await loadExcludedRoles(guildId)
      showStatus('Role removed from excluded list!')
      return true
    } catch (error) {
      console.error('Failed to remove excluded role:', error)
      showStatus('Failed to remove excluded role', 'error')
      return false
    }
  }

  // Leaderboard
  async function loadLeaderboard(guildId, limit = 100) {
    try {
      const response = await settingsApi.getLeaderboard(guildId, limit)
      // Backend now returns { data: [...], total, offset, limit }
      leaderboard.value = response.data?.data || response.data || []
      return leaderboard.value
    } catch (error) {
      console.error('Failed to load leaderboard:', error)
      return []
    }
  }

  async function resetUserXp(guildId, userId) {
    try {
      await settingsApi.resetUserXp(guildId, userId)
      leaderboard.value = []  // Clear first to avoid duplicates
      await loadLeaderboard(guildId)
      showStatus('User XP reset!')
      return true
    } catch (error) {
      console.error('Failed to reset user XP:', error)
      showStatus('Failed to reset user XP', 'error')
      return false
    }
  }

  async function setUserXp(guildId, userId, level, xp) {
    try {
      await settingsApi.setUserXp(guildId, userId, { level, xp })
      leaderboard.value = []  // Clear first to avoid duplicates
      await loadLeaderboard(guildId)
      showStatus('User XP updated!')
      return true
    } catch (error) {
      console.error('Failed to set user XP:', error)
      showStatus('Failed to set user XP', 'error')
      return false
    }
  }

  // Moderation
  async function loadModerationData(guildId) {
    try {
      const [rolesRes, logsRes] = await Promise.all([
        settingsApi.getModerationRoles(guildId),
        settingsApi.getModerationLogs(guildId, 10)
      ])
      moderationRoles.value = rolesRes.data || []
      moderationLogs.value = logsRes.data || []
    } catch (error) {
      console.error('Failed to load moderation data:', error)
    }
  }

  async function addModerationRole(guildId, roleId) {
    try {
      await settingsApi.addModerationRole(guildId, { role_id: roleId })
      moderationRoles.value.push(String(roleId))
      showStatus('Moderation role added!')
    } catch (error) {
      console.error('Failed to add moderation role:', error)
      showStatus('Failed to add moderation role', 'error')
    }
  }

  async function removeModerationRole(guildId, roleId) {
    try {
      await settingsApi.removeModerationRole(guildId, { role_id: roleId })
      moderationRoles.value = moderationRoles.value.filter(id => String(id) !== String(roleId))
      showStatus('Moderation role removed!')
    } catch (error) {
      console.error('Failed to remove moderation role:', error)
      showStatus('Failed to remove moderation role', 'error')
    }
  }

  // Welcome Roles
  async function loadWelcomeRoles(guildId) {
    try {
      const response = await settingsApi.getWelcomeRoles(guildId)
      welcomeRoles.value = response.data || []
      return welcomeRoles.value
    } catch (error) {
      console.error('Failed to load welcome roles:', error)
      return []
    }
  }

  // User Music Genres
  async function loadUserMusicGenres() {
    try {
      const response = await settingsApi.getUserMusicGenres()
      userMusicGenres.value = response.data || []
      return userMusicGenres.value
    } catch (error) {
      console.error('Failed to load user music genres:', error)
      return []
    }
  }

  async function addUserMusicGenre(genreData) {
    try {
      const response = await settingsApi.addUserMusicGenre(genreData)
      await loadUserMusicGenres()
      showStatus('Genre added successfully!')
      return true
    } catch (error) {
      console.error('Failed to add user music genre:', error)
      showStatus('Failed to add genre', 'error')
      return false
    }
  }

  async function deleteUserMusicGenre(genreId) {
    try {
      const response = await settingsApi.deleteUserMusicGenre(genreId)
      await loadUserMusicGenres()
      showStatus('Genre deleted successfully!')
      return true
    } catch (error) {
      console.error('Failed to delete user music genre:', error)
      showStatus('Failed to delete genre', 'error')
      return false
    }
  }

  return {
    // State
    guildSettings,
    chatbotSettings,
    levelingSettings,
    levelRoles,
    excludedRoles,
    leaderboard,
    moderationRoles,
    moderationLogs,
    welcomeRoles,
    userMusicGenres,
    loading,
    statusMessage,
    statusType,

    // Actions
    showStatus,
    loadGuildSettings,
    saveGuildSettings,
    loadChatbotSettings,
    saveChatbotSettings,
    loadLevelingSettings,
    saveLevelingSettings,
    toggleLeveling,
    loadLevelRoles,
    addLevelRole,
    updateLevelRole,
    removeLevelRole,
    loadExcludedRoles,
    addExcludedRole,
    removeExcludedRole,
    loadLeaderboard,
    resetUserXp,
    setUserXp,
    loadModerationData,
    addModerationRole,
    removeModerationRole,
    loadWelcomeRoles,
    loadUserMusicGenres,
    addUserMusicGenre,
    deleteUserMusicGenre
  }
})
