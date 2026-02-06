import axios from 'axios'

// Create axios instance with base URL (will use proxy in dev)
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor - add auth token if available
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('discord_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor - handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear token and redirect to login
      localStorage.removeItem('discord_token')
      localStorage.removeItem('discord_user')
      window.location.href = '/'
    }
    return Promise.reject(error)
  }
)

// Auth API
export const authApi = {
  getMe: () => api.get('/auth/me'),
  logout: () => api.get('/auth/logout'),

  getDiscordAuthUrl: () => {
    const clientId = import.meta.env.VITE_DISCORD_CLIENT_ID || ''
    const redirectUri = import.meta.env.VITE_REDIRECT_URI || 'http://localhost:5001/callback'
    return `https://discord.com/oauth2/authorize?client_id=${clientId}&response_type=code&redirect_uri=${encodeURIComponent(redirectUri)}&scope=identify%20guilds`
  }
}

// Guilds API
export const guildsApi = {
  getGuilds: () => api.get('/guilds'),
  getGuildChannels: (guildId) => api.get(`/guilds/${guildId}/channels`),
  getGuildRoles: (guildId) => api.get(`/guilds/${guildId}/roles`)
}

// Guild Settings API
export const settingsApi = {
  // Guild settings
  getGuildSettings: (guildId) => api.get(`/guilds/${guildId}/settings`),
  updateGuildSettings: (guildId, data) => api.put(`/guilds/${guildId}/settings`, data),

  // Chatbot
  getChatbotSettings: (guildId) => api.get(`/guilds/${guildId}/chatbot`),
  updateChatbotSettings: (guildId, data) => api.post(`/guilds/${guildId}/chatbot`, data),
  toggleChatbot: (guildId, enabled) => api.post(`/guilds/${guildId}/chatbot/toggle`, { enabled }),

  // Leveling
  getLevelingSettings: (guildId) => api.get(`/guilds/${guildId}/leveling`),
  updateLevelingSettings: (guildId, data) => api.post(`/guilds/${guildId}/leveling`, data),
  getLevelRoles: (guildId) => api.get(`/guilds/${guildId}/leveling/roles`),
  addLevelRole: (guildId, data) => api.post(`/guilds/${guildId}/leveling/roles`, data),
  updateLevelRole: (guildId, data) => api.put(`/guilds/${guildId}/leveling/roles`, data),
  removeLevelRole: (guildId, data) => api.delete(`/guilds/${guildId}/leveling/roles`, { data }),
  getLeaderboard: (guildId, limit = 10, offset = 0) =>
    api.get(`/guilds/${guildId}/leaderboard`, { params: { limit, offset } }),
  toggleLeveling: (guildId, enabled) => api.post(`/guilds/${guildId}/leveling/toggle`, { enabled }),
  resetUserXp: (guildId, userId) => api.post(`/guilds/${guildId}/users/${userId}/reset`),
  setUserXp: (guildId, userId, data) => api.post(`/guilds/${guildId}/users/${userId}/set`, data),
  getExcludedRoles: (guildId) => api.get(`/guilds/${guildId}/leveling/excluded-roles`),
  addExcludedRole: (guildId, data) => api.post(`/guilds/${guildId}/leveling/excluded-roles`, data),
  removeExcludedRole: (guildId, data) => api.delete(`/guilds/${guildId}/leveling/excluded-roles`, { data }),

  // Moderation
  getModerationRoles: (guildId) => api.get(`/guilds/${guildId}/moderation/roles`),
  addModerationRole: (guildId, data) => api.post(`/guilds/${guildId}/moderation/roles`, data),
  removeModerationRole: (guildId, data) => api.delete(`/guilds/${guildId}/moderation/roles`, { data }),
  getModerationLogs: (guildId, limit = 50) => api.get(`/guilds/${guildId}/moderation/logs`, { params: { limit } }),

  // Audit Logs
  getAuditLogs: (guildId, limit = 100) => api.get(`/guilds/${guildId}/audit-logs`, { params: { limit } }),

  // Members
  getMembers: (guildId, limit, offset, search) => api.get(`/guilds/${guildId}/members`, { params: { limit, offset, search } }),
  banMember: (guildId, userId, data) => api.post(`/guilds/${guildId}/members/${userId}/ban`, data),
  kickMember: (guildId, userId, data) => api.post(`/guilds/${guildId}/members/${userId}/kick`, data),
  timeoutMember: (guildId, userId, data) => api.post(`/guilds/${guildId}/members/${userId}/timeout`, data),
  removeTimeout: (guildId, userId) => api.delete(`/guilds/${guildId}/members/${userId}/timeout`),

  // Welcome
  getWelcomeRoles: (guildId) => api.get(`/guilds/${guildId}/welcome/roles`),
  addWelcomeRole: (guildId, data) => api.post(`/guilds/${guildId}/welcome/roles`, data),
  removeWelcomeRole: (guildId, data) => api.delete(`/guilds/${guildId}/welcome/roles`, { data }),

  // Music Genres (user-specific)
  getUserMusicGenres: () => api.get('/music/genres'),
  addUserMusicGenre: (data) => api.post('/music/genres', data),
  deleteUserMusicGenre: (genreId) => api.delete(`/music/genres/${genreId}`)
}

// File Upload
export const uploadApi = {
  uploadBanner: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    // Override Content-Type to let browser set multipart/form-data with boundary
    return api.post('/upload/banner', formData, {
      headers: {
        'Content-Type': undefined
      }
    })
  }
}

export default api
