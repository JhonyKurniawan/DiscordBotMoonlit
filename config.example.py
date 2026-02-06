"""
Discord Bot Configuration
=========================
Copy this file to config.py and fill in your credentials.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ==================== BOT CONFIGURATION ====================

# Database URL (PostgreSQL)
# Format: postgresql://user:password@host:port/dbname
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Bot Token dari Discord Developer Portal
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")

# Command prefix untuk bot
PREFIX = "!"

# ==================== DASHBOARD CONFIGURATION ====================

# Discord OAuth2 credentials (dari Discord Developer Portal)
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:5001/callback")
DASHBOARD_SECRET_KEY = os.getenv("DASHBOARD_SECRET_KEY", "")
DASHBOARD_BASE_URL = os.getenv("DASHBOARD_BASE_URL", "http://localhost:5001")


# ==================== WELCOME CONFIGURATION ====================

WELCOME_CHANNEL_ID = None
DEFAULT_ROLE_ID = None

# ==================== MUSIC CONFIGURATION ====================

DEFAULT_VOLUME = 100
AUTO_DISCONNECT_TIMEOUT = 300

# ==================== MODERATION CONFIGURATION ====================

DEFAULT_MUTE_DURATION = 10
MOD_LOG_CHANNEL_ID = None

# ==================== ROLE PERMISSIONS ====================

MODERATION_ROLE_IDS = None
WELCOME_ADMIN_ROLE_IDS = None

# ==================== LEVELING CONFIGURATION ====================

DEFAULT_XP_PER_MESSAGE = 10
DEFAULT_XP_COOLDOWN = 60
BASE_XP_PER_LEVEL = 100
XP_INCREMENT_PER_LEVEL = 50
LEVELING_ENABLED_BY_DEFAULT = True
LEVELING_ADMIN_ROLE_IDS = None

# ==================== CHATBOT CONFIGURATION ====================

# Groq API Key untuk chatbot (https://console.groq.com/keys)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"
DEFAULT_SYSTEM_PROMPT = "Kamu 'Nothing Bot', chatbot Discord sarkas yang lucu dan nyeleneh."
MAX_CHAT_HISTORY = 20
GROQ_TIMEOUT = 30

# ==================== MUSIC PROGRESS CONFIGURATION ====================

PROGRESS_UPDATE_INTERVAL = 1

# ==================== EMBED COLORS ====================

COLORS = {
    "success": 0x2ECC71,
    "error": 0xE74C3C,
    "warning": 0xF39C12,
    "info": 0x3498DB,
    "music": 0x9B59B6,
    "welcome": 0x1ABC9C,
    "leveling": 0xFFD700,
    "chatbot": 0x00D9FF,
}
