import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { guildsApi } from '@/services/api'

const GUILDS_CACHE_KEY = 'discord_guilds_cache'
const GUILDS_CACHE_DURATION = 5 * 60 * 1000 // 5 minutes
const CHANNELS_CACHE_KEY = 'discord_channels_cache_'
const CHANNELS_CACHE_DURATION = 5 * 60 * 1000 // 5 minutes
const ROLES_CACHE_KEY = 'discord_roles_cache_'
const ROLES_CACHE_DURATION = 5 * 60 * 1000 // 5 minutes

export const useGuildStore = defineStore('guild', () => {
  // State
  const guilds = ref([])
  const channels = ref({}) // { guildId: channels[] }
  const roles = ref({}) // { guildId: roles[] }
  const selectedGuildId = ref(null)
  const loading = ref(false)
  const channelsLoading = ref(false)
  const rolesLoading = ref(false)
  const loaded = ref(false) // Track if guilds have been loaded once

  // Getters
  const selectedGuild = computed(() => {
    if (!selectedGuildId.value) return null
    return guilds.value.find(g => String(g.id) === String(selectedGuildId.value))
  })

  const manageableGuilds = computed(() => {
    return guilds.value.filter(guild => canManageGuild(guild))
  })

  // Actions
  function canManageGuild(guild) {
    if (guild.owner) return true
    const permissions = parseInt(guild.permissions || 0)
    return (permissions & 0x8) === 0x8 // ADMINISTRATOR permission
  }

  // Get guild icon URL
  function getGuildIcon(guild) {
    if (!guild) return null
    if (guild.icon) {
      return `https://cdn.discordapp.com/icons/${guild.id}/${guild.icon}.png`
    }
    return null
  }

  // Get user avatar URL
  function getUserAvatar(user) {
    if (!user) return null
    if (user.avatar) {
      return `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png`
    }
    // Return default avatar based on discriminator
    const disc = user.discriminator || '0'
    if (disc === '0') {
      // New username system - use default avatar
      return `https://cdn.discordapp.com/embed/avatars/${parseInt(user.id) % 5}.png`
    }
    return `https://cdn.discordapp.com/embed/avatars/${(parseInt(disc) % 5)}.png`
  }

  function getCachedGuilds() {
    try {
      const cached = localStorage.getItem(GUILDS_CACHE_KEY)
      if (cached) {
        const { data, timestamp } = JSON.parse(cached)
        const age = Date.now() - timestamp
        if (age < GUILDS_CACHE_DURATION) {
          return data
        }
      }
    } catch (e) {
      console.error('Failed to read cached guilds:', e)
    }
    return null
  }

  function setCachedGuilds(data) {
    try {
      localStorage.setItem(GUILDS_CACHE_KEY, JSON.stringify({
        data,
        timestamp: Date.now()
      }))
    } catch (e) {
      console.error('Failed to cache guilds:', e)
    }
  }

  async function loadGuilds() {
    // Return cached data immediately if available
    const cached = getCachedGuilds()
    if (cached && cached.length > 0 && !loaded.value) {
      guilds.value = cached
      loaded.value = true
    }

    // Don't make API call if already loading
    if (loading.value) {
      return guilds.value
    }

    // Skip API call if we have fresh cached data
    if (cached && cached.length > 0) {
      // Refresh in background without showing loading
      loadGuildsInBackground()
      return guilds.value
    }

    loading.value = true
    try {
      const response = await guildsApi.getGuilds()
      guilds.value = response.data || []
      loaded.value = true
      setCachedGuilds(guilds.value)
      return guilds.value
    } catch (error) {
      console.error('Failed to load guilds:', error)
      return []
    } finally {
      loading.value = false
    }
  }

  async function loadGuildsInBackground() {
    try {
      const response = await guildsApi.getGuilds()
      if (response.data && response.data.length > 0) {
        guilds.value = response.data
        setCachedGuilds(guilds.value)
      }
    } catch (error) {
      console.error('Background guild load failed:', error)
    }
  }

  function selectGuild(guildId) {
    selectedGuildId.value = guildId
    // Save to localStorage for persistence
    localStorage.setItem('selected_guild_id', String(guildId))
  }

  function clearSelectedGuild() {
    selectedGuildId.value = null
    localStorage.removeItem('selected_guild_id')
  }

  // Channel functions
  function getCachedChannels(guildId) {
    try {
      const cached = localStorage.getItem(CHANNELS_CACHE_KEY + guildId)
      if (cached) {
        const { data, timestamp } = JSON.parse(cached)
        const age = Date.now() - timestamp
        if (age < CHANNELS_CACHE_DURATION) {
          return data
        }
      }
    } catch (e) {
      console.error('Failed to read cached channels:', e)
    }
    return null
  }

  function setCachedChannels(guildId, data) {
    try {
      localStorage.setItem(CHANNELS_CACHE_KEY + guildId, JSON.stringify({
        data,
        timestamp: Date.now()
      }))
    } catch (e) {
      console.error('Failed to cache channels:', e)
    }
  }

  async function loadChannels(guildId) {
    if (!guildId) return []

    // Return cached data immediately if available
    const cached = getCachedChannels(guildId)
    if (cached && cached.length > 0) {
      channels.value[guildId] = cached
    }

    // Check if currently loading
    if (channelsLoading.value) {
      return channels.value[guildId] || []
    }

    // Skip API call if we have fresh cached data
    if (cached && cached.length > 0) {
      // Refresh in background
      loadChannelsInBackground(guildId)
      return cached
    }

    channelsLoading.value = true
    try {
      const response = await guildsApi.getGuildChannels(guildId)
      const channelsData = response.data || []
      channels.value[guildId] = channelsData
      setCachedChannels(guildId, channelsData)
      return channelsData
    } catch (error) {
      console.error('Failed to load channels:', error)
      return []
    } finally {
      channelsLoading.value = false
    }
  }

  async function loadChannelsInBackground(guildId) {
    try {
      const response = await guildsApi.getGuildChannels(guildId)
      if (response.data) {
        channels.value[guildId] = response.data
        setCachedChannels(guildId, response.data)
      }
    } catch (error) {
      console.error('Background channel load failed:', error)
    }
  }

  function getChannels(guildId) {
    return channels.value[guildId] || []
  }

  function getChannelOptions(guildId) {
    const chans = getChannels(guildId)
    return chans.map(ch => ({
      value: ch.id,
      label: ch.name,
      icon: '#'
    }))
  }

  // Role functions
  function getCachedRoles(guildId) {
    try {
      const cached = localStorage.getItem(ROLES_CACHE_KEY + guildId)
      if (cached) {
        const { data, timestamp } = JSON.parse(cached)
        const age = Date.now() - timestamp
        if (age < ROLES_CACHE_DURATION) {
          return data
        }
      }
    } catch (e) {
      console.error('Failed to read cached roles:', e)
    }
    return null
  }

  function setCachedRoles(guildId, data) {
    try {
      localStorage.setItem(ROLES_CACHE_KEY + guildId, JSON.stringify({
        data,
        timestamp: Date.now()
      }))
    } catch (e) {
      console.error('Failed to cache roles:', e)
    }
  }

  async function loadRoles(guildId) {
    if (!guildId) return []

    // Return cached data immediately if available
    const cached = getCachedRoles(guildId)
    if (cached && cached.length > 0) {
      roles.value[guildId] = cached
    }

    // Check if currently loading
    if (rolesLoading.value) {
      return roles.value[guildId] || []
    }

    // Skip API call if we have fresh cached data
    if (cached && cached.length > 0) {
      // Refresh in background
      loadRolesInBackground(guildId)
      return cached
    }

    rolesLoading.value = true
    try {
      const response = await guildsApi.getGuildRoles(guildId)
      const rolesData = response.data || []
      roles.value[guildId] = rolesData
      setCachedRoles(guildId, rolesData)
      return rolesData
    } catch (error) {
      console.error('Failed to load roles:', error)
      return []
    } finally {
      rolesLoading.value = false
    }
  }

  async function loadRolesInBackground(guildId) {
    try {
      const response = await guildsApi.getGuildRoles(guildId)
      if (response.data) {
        roles.value[guildId] = response.data
        setCachedRoles(guildId, response.data)
      }
    } catch (error) {
      console.error('Background role load failed:', error)
    }
  }

  function getRoles(guildId) {
    return roles.value[guildId] || []
  }

  function getRoleOptions(guildId) {
    const roleList = getRoles(guildId)
    return roleList.map(r => ({
      value: String(r.id),  // Convert to string to avoid precision loss with large IDs
      label: r.name,
      icon: '@',
      color: r.color
    }))
  }

  return {
    guilds,
    channels,
    roles,
    selectedGuildId,
    selectedGuild,
    loading,
    channelsLoading,
    rolesLoading,
    loaded,
    manageableGuilds,
    canManageGuild,
    getGuildIcon,
    getUserAvatar,
    loadGuilds,
    loadChannels,
    loadRoles,
    getChannels,
    getRoles,
    getChannelOptions,
    getRoleOptions,
    selectGuild,
    clearSelectedGuild
  }
})
