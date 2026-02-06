import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useGuildStore } from '@/stores/guild'
import LoginView from '@/views/LoginView.vue'
import CallbackView from '@/views/CallbackView.vue'
import ServerSelectView from '@/views/ServerSelectView.vue'
import DashboardView from '@/views/DashboardView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'login',
      component: LoginView,
      meta: { requiresAuth: false }
    },
    {
      path: '/callback',
      name: 'callback',
      component: CallbackView,
      meta: { requiresAuth: false }
    },
    {
      path: '/servers',
      name: 'servers',
      component: ServerSelectView,
      meta: { requiresAuth: true }
    },
    {
      path: '/dashboard/:guildId',
      component: DashboardView,
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'guild-overview',
          component: () => import('@/views/settings/OverviewView.vue'),
          meta: { requiresAuth: true }
        },
        {
          path: 'overview',
          redirect: ''
        },
        {
          path: 'leveling',
          name: 'guild-leveling',
          component: () => import('@/views/settings/LevelingView.vue'),
          meta: { requiresAuth: true }
        },
        {
          path: 'chatbot',
          name: 'guild-chatbot',
          component: () => import('@/views/settings/ChatbotView.vue'),
          meta: { requiresAuth: true }
        },
        {
          path: 'music',
          name: 'guild-music',
          component: () => import('@/views/settings/MusicView.vue'),
          meta: { requiresAuth: true }
        },
        {
          path: 'moderation',
          name: 'guild-moderation',
          component: () => import('@/views/settings/ModerationView.vue'),
          meta: { requiresAuth: true }
        },
        {
          path: 'logs',
          name: 'guild-logs',
          component: () => import('@/views/settings/LogView.vue'),
          meta: { requiresAuth: true }
        },
        {
          path: 'settings',
          name: 'guild-settings',
          component: () => import('@/views/settings/SettingsView.vue'),
          meta: { requiresAuth: true }
        }
      ]
    },
    {
      path: '/dashboard',
      redirect: '/servers'
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/'
    }
  ]
})

// Navigation guard for auth
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  const guildStore = useGuildStore()

  // Initialize auth from storage if needed
  if (!authStore.user && authStore.token) {
    authStore.initFromStorage()
  }

  // Handle callback route
  if (to.name === 'callback') {
    const urlParams = new URLSearchParams(window.location.search)
    const token = urlParams.get('token')
    const user = urlParams.get('user')
    const userId = urlParams.get('user_id')

    if (token && userId) {
      // Clear any previously selected guild
      guildStore.clearSelectedGuild()

      // Store auth data
      authStore.setToken(token)
      authStore.setUser({
        username: user,
        id: userId,
        discriminator: urlParams.get('discriminator') || '0',
        avatar: urlParams.get('avatar') || ''
      })

      // Load guilds and redirect
      await guildStore.loadGuilds()
      if (guildStore.manageableGuilds.length === 1) {
        // Only one guild, go directly to dashboard
        const guildId = guildStore.manageableGuilds[0].id
        guildStore.selectGuild(guildId)
        next({ name: 'guild-overview', params: { guildId }, replace: true })
      } else {
        // Multiple guilds, go to server selection
        next({ name: 'servers', replace: true })
      }
      return
    } else {
      // No token, redirect to login
      next({ name: 'login', replace: true })
      return
    }
  }

  const requiresAuth = to.meta.requiresAuth

  if (requiresAuth && !authStore.isLoggedIn) {
    // Try to check auth status first
    const isValid = await authStore.checkAuth()
    if (!isValid) {
      next({ name: 'login' })
      return
    }
  }

  if (to.name === 'login' && authStore.isLoggedIn) {
    // Clear any selected guild and load guilds
    guildStore.clearSelectedGuild()
    await guildStore.loadGuilds()
    if (guildStore.manageableGuilds.length === 1) {
      next({ name: 'guild-overview', params: { guildId: guildStore.manageableGuilds[0].id } })
      return
    }
    next({ name: 'servers' })
    return
  }

  // Clear selected guild when going to servers page
  if (to.name === 'servers') {
    guildStore.clearSelectedGuild()
  }

  // For dashboard routes, set guild from route immediately (load in background)
  if (to.name?.startsWith('guild-')) {
    if (to.params.guildId) {
      guildStore.selectGuild(to.params.guildId)
    }
    // Load guilds in background if not loaded
    if (guildStore.guilds.length === 0) {
      guildStore.loadGuilds()
    }
  }

  next()
})

export default router
