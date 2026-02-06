"""
Database module for Discord Bot
Uses SQLite for persistent storage
"""

import sqlite3
import os
import sys
import threading
from typing import Optional, Dict, List, Tuple, Any

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Default system prompt (fallback if config not available)
DEFAULT_SYSTEM_PROMPT = ""  # Empty - let AI use its default behavior
try:
    from config import DEFAULT_SYSTEM_PROMPT as CONFIG_DEFAULT_PROMPT
    if CONFIG_DEFAULT_PROMPT:
        DEFAULT_SYSTEM_PROMPT = CONFIG_DEFAULT_PROMPT
except ImportError:
    pass

# Thread-local storage for database connections
_local = threading.local()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")

# Try to load from config if not in env
if not DATABASE_URL:
    try:
        from config import DATABASE_URL as CONFIG_DB_URL
        DATABASE_URL = CONFIG_DB_URL
    except ImportError:
        pass

IS_POSTGRES = DATABASE_URL and DATABASE_URL.startswith("postgres")

# SQLite fallback path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'bot_database.db')

if IS_POSTGRES:
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        DBError = psycopg2.Error
    except ImportError:
        print("psycopg2 not installed. Please install it with: pip install psycopg2-binary")
        sys.exit(1)
else:
    DBError = sqlite3.Error


class PostgresCursorWrapper:
    """Wrapper to make psycopg2 cursor behave more like sqlite3 cursor for param substitution."""
    def __init__(self, cursor):
        self.cursor = cursor
        
    def execute(self, query, params=None):
        # Convert ? to %s for PostgreSQL
        # This is a simple replacement, assuming ? isn't used in string literals
        # For a more robust solution, we would need a proper SQL parser, 
        # but this should work for our specific queries.
        pg_query = query.replace('?', '%s')
        if params is None:
            return self.cursor.execute(pg_query)
        return self.cursor.execute(pg_query, params)
        
    def executemany(self, query, params):
        pg_query = query.replace('?', '%s')
        return self.cursor.executemany(pg_query, params)
        
    def fetchone(self):
        return self.cursor.fetchone()
        
    def fetchall(self):
        return self.cursor.fetchall()
        
    def __getattr__(self, name):
        return getattr(self.cursor, name)

class PostgresConnectionWrapper:
    """Wrapper for Postgres connection."""
    def __init__(self, conn):
        self.conn = conn
        
    def cursor(self):
        return PostgresCursorWrapper(self.conn.cursor(cursor_factory=RealDictCursor))
        
    def commit(self):
        return self.conn.commit()
        
    def rollback(self):
        return self.conn.rollback()

    def close(self):
        return self.conn.close()




def get_connection():
    """Get a thread-local database connection."""
    if not hasattr(_local, 'conn') or _local.conn is None or (IS_POSTGRES and _local.conn.conn.closed):
        if IS_POSTGRES:
            try:
                # Connect to PostgreSQL
                pg_conn = psycopg2.connect(DATABASE_URL)
                pg_conn.autocommit = True
                _local.conn = PostgresConnectionWrapper(pg_conn)
            except Exception as e:
                print(f"Failed to connect to PostgreSQL: {e}")
                # Fallback to SQLite if Postgres fails? 
                # For now let's raise the error to be explicit
                raise e
        else:
            # Connect to SQLite
            _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            _local.conn.row_factory = sqlite3.Row
            
    return _local.conn


def init_db() -> bool:
    """
    Initialize database tables.
    Returns True if successful, False otherwise.
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Define table schemas based on DB type
        pk_type = "SERIAL PRIMARY KEY" if IS_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"
        bool_type = "BOOLEAN" if IS_POSTGRES else "BOOLEAN" # Postgres has native boolean
        
        # Guild settings table
        if IS_POSTGRES:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id BIGINT PRIMARY KEY,
                    music_auto_delete BOOLEAN DEFAULT TRUE,
                    music_default_volume INTEGER DEFAULT 50,
                    music_shuffle BOOLEAN DEFAULT FALSE,
                    music_repeat BOOLEAN DEFAULT FALSE,
                    welcome_channel_id BIGINT,
                    welcome_message TEXT DEFAULT 'Welcome {user} to the server!',
                    welcome_enabled BOOLEAN DEFAULT FALSE,
                    goodbye_channel_id BIGINT,
                    goodbye_message TEXT DEFAULT 'Goodbye {user}!',
                    goodbye_enabled BOOLEAN DEFAULT FALSE,
                    auto_role_enabled BOOLEAN DEFAULT FALSE,
                    auto_role_id BIGINT,
                    moderation_log_channel_id BIGINT,
                    prefix TEXT DEFAULT '!'
                )
            ''')
        else:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER PRIMARY KEY,
                    music_auto_delete BOOLEAN DEFAULT 1,
                    music_default_volume INTEGER DEFAULT 50,
                    music_shuffle BOOLEAN DEFAULT 0,
                    music_repeat BOOLEAN DEFAULT 0,
                    welcome_channel_id INTEGER,
                    welcome_message TEXT DEFAULT 'Welcome {user} to the server!',
                    welcome_enabled BOOLEAN DEFAULT 0,
                    goodbye_channel_id INTEGER,
                    goodbye_message TEXT DEFAULT 'Goodbye {user}!',
                    goodbye_enabled BOOLEAN DEFAULT 0,
                    auto_role_enabled BOOLEAN DEFAULT 0,
                    auto_role_id INTEGER,
                    moderation_log_channel_id INTEGER,
                    prefix TEXT DEFAULT '!'
                )
            ''')

        # Add welcome/goodbye image settings columns if they don't exist
        # This is for migrations - adding new columns to existing databases
        
        # Define column types for SQLite vs Postgres
        col_definitions = {
            'use_image': 'INTEGER DEFAULT 0' if not IS_POSTGRES else 'BOOLEAN DEFAULT FALSE',
            'banner_url': 'TEXT',
            'welcome_text': 'TEXT DEFAULT "WELCOME"' if not IS_POSTGRES else "TEXT DEFAULT 'WELCOME'",
            'profile_position': 'TEXT DEFAULT "center"' if not IS_POSTGRES else "TEXT DEFAULT 'center'",
            'text_color': 'TEXT DEFAULT "#FFD700"' if not IS_POSTGRES else "TEXT DEFAULT '#FFD700'",
            'font_family': 'TEXT DEFAULT "arial"' if not IS_POSTGRES else "TEXT DEFAULT 'arial'",
            'banner_offset_x': 'INTEGER DEFAULT 0',
            'banner_offset_y': 'INTEGER DEFAULT 0',
            'avatar_offset_x': 'INTEGER DEFAULT 0',
            'avatar_offset_y': 'INTEGER DEFAULT 0',
            'text_offset_x': 'INTEGER DEFAULT 0',
            'text_offset_y': 'INTEGER DEFAULT 0',
            'send_gif_as_is': 'INTEGER DEFAULT 0' if not IS_POSTGRES else 'BOOLEAN DEFAULT FALSE',
            'send_banner_as_is': 'INTEGER DEFAULT 0' if not IS_POSTGRES else 'BOOLEAN DEFAULT FALSE',
            'welcome_text_size': 'INTEGER DEFAULT 56',
            'username_text_size': 'INTEGER DEFAULT 32',
            'avatar_size': 'INTEGER DEFAULT 180',
            'use_goodbye_image': 'INTEGER DEFAULT 0' if not IS_POSTGRES else 'BOOLEAN DEFAULT FALSE',
            'goodbye_text': 'TEXT DEFAULT "GOODBYE"' if not IS_POSTGRES else "TEXT DEFAULT 'GOODBYE'",
            'goodbye_text_color': 'TEXT DEFAULT "#FF6B6B"' if not IS_POSTGRES else "TEXT DEFAULT '#FF6B6B'",
            'goodbye_profile_position': 'TEXT DEFAULT "center"' if not IS_POSTGRES else "TEXT DEFAULT 'center'",
            'goodbye_font_family': 'TEXT DEFAULT "arial"' if not IS_POSTGRES else "TEXT DEFAULT 'arial'",
            'goodbye_banner_url': 'TEXT',
            'goodbye_banner_offset_x': 'INTEGER DEFAULT 0',
            'goodbye_banner_offset_y': 'INTEGER DEFAULT 0',
            'goodbye_avatar_offset_x': 'INTEGER DEFAULT 0',
            'goodbye_avatar_offset_y': 'INTEGER DEFAULT 0',
            'goodbye_text_offset_x': 'INTEGER DEFAULT 0',
            'goodbye_text_offset_y': 'INTEGER DEFAULT 0',
            'goodbye_send_gif_as_is': 'INTEGER DEFAULT 0' if not IS_POSTGRES else 'BOOLEAN DEFAULT FALSE',
            'goodbye_send_banner_as_is': 'INTEGER DEFAULT 0' if not IS_POSTGRES else 'BOOLEAN DEFAULT FALSE',
            'welcome_text_bold': 'INTEGER DEFAULT 0' if not IS_POSTGRES else 'BOOLEAN DEFAULT FALSE',
            'welcome_text_italic': 'INTEGER DEFAULT 0' if not IS_POSTGRES else 'BOOLEAN DEFAULT FALSE',
            'welcome_text_underline': 'INTEGER DEFAULT 0' if not IS_POSTGRES else 'BOOLEAN DEFAULT FALSE',
            'username_text_bold': 'INTEGER DEFAULT 0' if not IS_POSTGRES else 'BOOLEAN DEFAULT FALSE',
            'username_text_italic': 'INTEGER DEFAULT 0' if not IS_POSTGRES else 'BOOLEAN DEFAULT FALSE',
            'username_text_underline': 'INTEGER DEFAULT 0' if not IS_POSTGRES else 'BOOLEAN DEFAULT FALSE',
            'goodbye_text_bold': 'INTEGER DEFAULT 0' if not IS_POSTGRES else 'BOOLEAN DEFAULT FALSE',
            'goodbye_text_italic': 'INTEGER DEFAULT 0' if not IS_POSTGRES else 'BOOLEAN DEFAULT FALSE',
            'goodbye_text_underline': 'INTEGER DEFAULT 0' if not IS_POSTGRES else 'BOOLEAN DEFAULT FALSE',
            'goodbye_username_text_bold': 'INTEGER DEFAULT 0' if not IS_POSTGRES else 'BOOLEAN DEFAULT FALSE',
            'goodbye_username_text_italic': 'INTEGER DEFAULT 0' if not IS_POSTGRES else 'BOOLEAN DEFAULT FALSE',
            'goodbye_username_text_underline': 'INTEGER DEFAULT 0' if not IS_POSTGRES else 'BOOLEAN DEFAULT FALSE',
            'google_font_family': 'TEXT',
            'custom_font_path': 'TEXT',
            'avatar_shape': 'TEXT DEFAULT "circle"' if not IS_POSTGRES else "TEXT DEFAULT 'circle'",
            'avatar_border_enabled': 'INTEGER DEFAULT 1' if not IS_POSTGRES else 'BOOLEAN DEFAULT TRUE',
            'avatar_border_width': 'INTEGER DEFAULT 6',
            'avatar_border_color': 'TEXT DEFAULT "#FFFFFF"' if not IS_POSTGRES else "TEXT DEFAULT '#FFFFFF'",
            'goodbye_avatar_shape': 'TEXT DEFAULT "circle"' if not IS_POSTGRES else "TEXT DEFAULT 'circle'",
            'goodbye_avatar_border_enabled': 'INTEGER DEFAULT 1' if not IS_POSTGRES else 'BOOLEAN DEFAULT TRUE',
            'goodbye_avatar_border_width': 'INTEGER DEFAULT 6',
            'goodbye_avatar_border_color': 'TEXT DEFAULT "#FFFFFF"' if not IS_POSTGRES else "TEXT DEFAULT '#FFFFFF'",
            'goodbye_avatar_size': 'INTEGER DEFAULT 180',
            'goodbye_welcome_text_size': 'INTEGER DEFAULT 56',
            'goodbye_username_text_size': 'INTEGER DEFAULT 32',
            'auto_role_ids': 'TEXT DEFAULT ""' if not IS_POSTGRES else "TEXT DEFAULT ''",
            'music_channel_id': 'BIGINT' if IS_POSTGRES else 'INTEGER',
            'auto_disconnect_time': 'INTEGER DEFAULT 300',
        }

        new_columns = [(k, v) for k, v in col_definitions.items()]

        # Get existing columns
        if IS_POSTGRES:
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'guild_settings'")
            existing_columns = {row['column_name'] for row in cursor.fetchall()}
        else:
            cursor.execute("PRAGMA table_info(guild_settings)")
            existing_columns = {row[1] for row in cursor.fetchall()}

        # Add missing columns
        for column_name, column_def in new_columns:
            if column_name not in existing_columns:
                try:
                    cursor.execute(f'ALTER TABLE guild_settings ADD COLUMN {column_name} {column_def}')
                    print(f"[DB] Added column: {column_name}")
                except Exception as e:
                    print(f"[DB] Error adding column {column_name}: {e}")

        # Chatbot settings table
        if IS_POSTGRES:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chatbot_settings (
                    guild_id BIGINT PRIMARY KEY,
                    enabled BOOLEAN DEFAULT FALSE,
                    model_name TEXT DEFAULT 'llama-3.3-70b-versatile',
                    max_history INTEGER DEFAULT 10,
                    system_prompt TEXT,
                    temperature REAL DEFAULT 0.7,
                    channel_whitelist TEXT,
                    enabled_channels TEXT,
                    api_key TEXT
                )
            ''')
        else:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chatbot_settings (
                    guild_id INTEGER PRIMARY KEY,
                    enabled BOOLEAN DEFAULT 0,
                    model_name TEXT DEFAULT 'llama-3.3-70b-versatile',
                    max_history INTEGER DEFAULT 10,
                    system_prompt TEXT,
                    temperature REAL DEFAULT 0.7,
                    channel_whitelist TEXT,
                    enabled_channels TEXT,
                    api_key TEXT
                )
            ''')

        # Add missing columns to chatbot_settings (for existing databases)
        # Add missing columns to chatbot_settings (for existing databases)
        if IS_POSTGRES:
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'chatbot_settings'")
            existing_chatbot_columns = {row['column_name'] for row in cursor.fetchall()}
        else:
            cursor.execute("PRAGMA table_info(chatbot_settings)")
            existing_chatbot_columns = {row[1] for row in cursor.fetchall()}

        chatbot_new_columns = [
            ('enabled_channels', 'TEXT'),
            ('api_key', 'TEXT')
        ]

        for column_name, column_def in chatbot_new_columns:
            if column_name not in existing_chatbot_columns:
                try:
                    cursor.execute(f'ALTER TABLE chatbot_settings ADD COLUMN {column_name} {column_def}')
                    print(f"[DB] Added chatbot_settings column: {column_name}")
                except Exception as e:
                    print(f"[DB] Error adding chatbot_settings column {column_name}: {e}")

        # Chat history table
        if IS_POSTGRES:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_history (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT NOT NULL,
                    channel_id BIGINT NOT NULL,
                    user_id BIGINT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id) ON DELETE CASCADE
                )
            ''')
        else:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id) ON DELETE CASCADE
                )
            ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_history_guild_channel ON chat_history(guild_id, channel_id)')

        # Leveling settings table
        if IS_POSTGRES:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS leveling_settings (
                    guild_id BIGINT PRIMARY KEY,
                    enabled BOOLEAN DEFAULT FALSE,
                    xp_per_message INTEGER DEFAULT 10,
                    xp_per_minute REAL DEFAULT 60.0,
                    cooldown_seconds INTEGER DEFAULT 60,
                    level_up_announcements BOOLEAN DEFAULT TRUE,
                    level_up_channel_id BIGINT,
                    xp_multiplier REAL DEFAULT 1.0
                )
            ''')
        else:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS leveling_settings (
                    guild_id INTEGER PRIMARY KEY,
                    enabled BOOLEAN DEFAULT 0,
                    xp_per_message INTEGER DEFAULT 10,
                    xp_per_minute REAL DEFAULT 60.0,
                    cooldown_seconds INTEGER DEFAULT 60,
                    level_up_announcements BOOLEAN DEFAULT 1,
                    level_up_channel_id INTEGER,
                    xp_multiplier REAL DEFAULT 1.0
                )
            ''')
        # Add min_message_length column if not exists (for existing databases)
        try:
            cursor.execute('ALTER TABLE leveling_settings ADD COLUMN min_message_length INTEGER DEFAULT 0')
        except Exception:
            pass  # Column already exists

        # User XP table
        if IS_POSTGRES:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_xp (
                    guild_id BIGINT NOT NULL,
                    user_id BIGINT NOT NULL,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    message_count INTEGER DEFAULT 0,
                    total_xp BIGINT DEFAULT 0,
                    last_xp_gain TIMESTAMP,
                    PRIMARY KEY (guild_id, user_id),
                    FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id) ON DELETE CASCADE
                )
            ''')
        else:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_xp (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    message_count INTEGER DEFAULT 0,
                    total_xp INTEGER DEFAULT 0,
                    last_xp_gain DATETIME,
                    PRIMARY KEY (guild_id, user_id),
                    FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id) ON DELETE CASCADE
                )
            ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_xp_level ON user_xp(guild_id, level DESC, xp DESC)')

        # Level roles table
        if IS_POSTGRES:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS level_roles (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT NOT NULL,
                    level INTEGER NOT NULL,
                    role_id BIGINT NOT NULL,
                    stack BOOLEAN DEFAULT FALSE,
                    UNIQUE(guild_id, level, role_id),
                    FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id) ON DELETE CASCADE
                )
            ''')
        else:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS level_roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    level INTEGER NOT NULL,
                    role_id INTEGER NOT NULL,
                    stack BOOLEAN DEFAULT 0,
                    UNIQUE(guild_id, level, role_id),
                    FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id) ON DELETE CASCADE
                )
            ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_level_roles_guild ON level_roles(guild_id, level)')

        # Excluded roles table (roles that cannot gain XP)
        if IS_POSTGRES:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS excluded_roles (
                    guild_id BIGINT NOT NULL,
                    role_id BIGINT NOT NULL,
                    PRIMARY KEY (guild_id, role_id),
                    FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id) ON DELETE CASCADE
                )
            ''')
        else:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS excluded_roles (
                    guild_id INTEGER NOT NULL,
                    role_id INTEGER NOT NULL,
                    PRIMARY KEY (guild_id, role_id),
                    FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id) ON DELETE CASCADE
                )
            ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_excluded_roles_guild ON excluded_roles(guild_id)')

        # Moderation roles table
        if IS_POSTGRES:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS moderation_roles (
                    guild_id BIGINT NOT NULL,
                    role_id BIGINT NOT NULL,
                    permissions TEXT DEFAULT 'all',
                    PRIMARY KEY (guild_id, role_id),
                    FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id) ON DELETE CASCADE
                )
            ''')
        else:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS moderation_roles (
                    guild_id INTEGER NOT NULL,
                    role_id INTEGER NOT NULL,
                    permissions TEXT DEFAULT 'all',
                    PRIMARY KEY (guild_id, role_id),
                    FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id) ON DELETE CASCADE
                )
            ''')

        # Moderation logs table
        if IS_POSTGRES:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS moderation_logs (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT NOT NULL,
                    moderator_id BIGINT NOT NULL,
                    user_id BIGINT NOT NULL,
                    action TEXT NOT NULL,
                    reason TEXT,
                    duration INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id) ON DELETE CASCADE
                )
            ''')
        else:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS moderation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    moderator_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    reason TEXT,
                    duration INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id) ON DELETE CASCADE
                )
            ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_moderation_logs_guild ON moderation_logs(guild_id, timestamp DESC)')

        # Welcome roles table
        if IS_POSTGRES:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS welcome_roles (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT NOT NULL,
                    role_id BIGINT NOT NULL,
                    UNIQUE(guild_id, role_id),
                    FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id) ON DELETE CASCADE
                )
            ''')
        else:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS welcome_roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    role_id INTEGER NOT NULL,
                    UNIQUE(guild_id, role_id),
                    FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id) ON DELETE CASCADE
                )
            ''')

        # Audit logs table (dashboard changes)
        if IS_POSTGRES:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT NOT NULL,
                    user_id BIGINT NOT NULL,
                    user_name TEXT NOT NULL,
                    action TEXT NOT NULL,
                    category TEXT NOT NULL,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id) ON DELETE CASCADE
                )
            ''')
        else:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    user_name TEXT NOT NULL,
                    action TEXT NOT NULL,
                    category TEXT NOT NULL,
                    details TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id) ON DELETE CASCADE
                )
            ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_logs_guild ON audit_logs(guild_id, timestamp DESC)')

        # User music genres table (per-user custom music genres)
        if IS_POSTGRES:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_music_genres (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    genre_name TEXT NOT NULL,
                    search_query TEXT NOT NULL,
                    emoji TEXT DEFAULT '🎵',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, genre_name)
                )
            ''')
        else:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_music_genres (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    genre_name TEXT NOT NULL,
                    search_query TEXT NOT NULL,
                    emoji TEXT DEFAULT '🎵',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, genre_name)
                )
            ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_music_genres_user ON user_music_genres(user_id)')

        # Migration: Add goodbye columns if they don't exist
        if not IS_POSTGRES:
            try:
                cursor.execute("SELECT goodbye_enabled FROM guild_settings LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE guild_settings ADD COLUMN goodbye_channel_id INTEGER")
                cursor.execute("ALTER TABLE guild_settings ADD COLUMN goodbye_message TEXT DEFAULT 'Goodbye {user}!'")
                cursor.execute("ALTER TABLE guild_settings ADD COLUMN goodbye_enabled BOOLEAN DEFAULT 0")

        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Database initialization error: {e}")
        conn.rollback()
        return False


# ============================================================================
# GUILD SETTINGS
# ============================================================================

def get_guild_settings(guild_id: int) -> Dict[str, Any]:
    """Get guild settings. Creates default settings if not exists."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM guild_settings WHERE guild_id = ?', (guild_id,))
    row = cursor.fetchone()

    if row is None:
        # Create default settings
        default_settings = {
            'guild_id': guild_id,
            'music_auto_delete': 1,
            'music_default_volume': 50,
            'music_shuffle': 0,
            'music_repeat': 0,
            'welcome_channel_id': None,
            'welcome_message': 'Welcome {user} to the server!',
            'welcome_enabled': 0,
            'goodbye_channel_id': None,
            'goodbye_message': 'Goodbye {user}!',
            'goodbye_enabled': 0,
            'auto_role_enabled': 0,
            'auto_role_id': None,
            'auto_role_ids': '',  # Multiple roles (comma-separated)
            'moderation_log_channel_id': None,
            'music_channel_id': None,
            'auto_disconnect_time': 300,  # 5 minutes default
            'prefix': '!',
            # Welcome Image defaults
            'use_image': 0,
            'banner_url': None,
            'welcome_text': 'WELCOME',
            'profile_position': 'center',
            'text_color': '#FFD700',
            'font_family': 'arial',
            'banner_offset_x': 0,
            'banner_offset_y': 0,
            'avatar_offset_x': 0,
            'avatar_offset_y': 0,
            'text_offset_x': 0,
            'text_offset_y': 0,
            'send_gif_as_is': 0,
            'send_banner_as_is': 0,
            'welcome_text_size': 56,
            'username_text_size': 32,
            'avatar_size': 180,
            # Goodbye Image defaults
            'use_goodbye_image': 0,
            'goodbye_text': 'GOODBYE',
            'goodbye_text_color': '#FF6B6B',
            'goodbye_profile_position': 'center',
            'goodbye_font_family': 'arial',
            'goodbye_banner_url': None,
            'goodbye_banner_offset_x': 0,
            'goodbye_banner_offset_y': 0,
            'goodbye_avatar_offset_x': 0,
            'goodbye_avatar_offset_y': 0,
            'goodbye_text_offset_x': 0,
            'goodbye_text_offset_y': 0,
            'goodbye_send_gif_as_is': 0,
            'goodbye_send_banner_as_is': 0,
            # Text style defaults
            'welcome_text_bold': 0,
            'welcome_text_italic': 0,
            'welcome_text_underline': 0,
            'username_text_bold': 0,
            'username_text_italic': 0,
            'username_text_underline': 0,
            'goodbye_text_bold': 0,
            'goodbye_text_italic': 0,
            'goodbye_text_underline': 0,
            'goodbye_username_text_bold': 0,
            'goodbye_username_text_italic': 0,
            'goodbye_username_text_underline': 0,
            # Font defaults
            'google_font_family': None,
            'custom_font_path': None,
            # Avatar shape default
            'avatar_shape': 'circle',
            'goodbye_avatar_shape': 'circle',
            # Avatar border defaults
            'avatar_border_enabled': 1,
            'avatar_border_width': 6,
            'avatar_border_color': '#FFFFFF',
            'goodbye_avatar_border_enabled': 1,
            'goodbye_avatar_border_width': 6,
            'goodbye_avatar_border_color': '#FFFFFF',
            # Avatar size defaults
            'avatar_size': 180,
            'goodbye_avatar_size': 180,
            # Text size defaults
            'welcome_text_size': 56,
            'username_text_size': 32,
            'goodbye_welcome_text_size': 56,
            'goodbye_username_text_size': 32,
        }
        cursor.execute('''
            INSERT INTO guild_settings (
                guild_id, music_auto_delete, music_default_volume, music_shuffle, music_repeat,
                welcome_channel_id, welcome_message, welcome_enabled,
                goodbye_channel_id, goodbye_message, goodbye_enabled,
                auto_role_enabled, auto_role_id, moderation_log_channel_id, music_channel_id, prefix,
                use_image, banner_url, welcome_text, profile_position,
                text_color, font_family, banner_offset_x, banner_offset_y, avatar_offset_x, avatar_offset_y,
                text_offset_x, text_offset_y, send_gif_as_is, send_banner_as_is,
                welcome_text_size, username_text_size,
                use_goodbye_image, goodbye_text, goodbye_text_color, goodbye_profile_position,
                goodbye_font_family, goodbye_banner_url, goodbye_banner_offset_x, goodbye_banner_offset_y,
                goodbye_avatar_offset_x, goodbye_avatar_offset_y, goodbye_text_offset_x, goodbye_text_offset_y,
                goodbye_send_gif_as_is, goodbye_send_banner_as_is,
                welcome_text_bold, welcome_text_italic, welcome_text_underline,
                username_text_bold, username_text_italic, username_text_underline,
                goodbye_text_bold, goodbye_text_italic, goodbye_text_underline,
                goodbye_username_text_bold, goodbye_username_text_italic, goodbye_username_text_underline,
                google_font_family, custom_font_path, avatar_shape, goodbye_avatar_shape,
                avatar_border_enabled, avatar_border_width, avatar_border_color, goodbye_avatar_border_enabled, goodbye_avatar_border_width, goodbye_avatar_border_color,
                avatar_size, goodbye_avatar_size,
                goodbye_welcome_text_size, goodbye_username_text_size
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            guild_id, default_settings['music_auto_delete'], default_settings['music_default_volume'],
            default_settings['music_shuffle'], default_settings['music_repeat'],
            default_settings['welcome_channel_id'], default_settings['welcome_message'],
            default_settings['welcome_enabled'],
            default_settings['goodbye_channel_id'], default_settings['goodbye_message'],
            default_settings['goodbye_enabled'],
            default_settings['auto_role_enabled'], default_settings['auto_role_id'],
            default_settings['moderation_log_channel_id'], default_settings['music_channel_id'], default_settings['auto_disconnect_time'], default_settings['prefix'],
            default_settings['use_image'], default_settings['banner_url'], default_settings['welcome_text'],
            default_settings['profile_position'], default_settings['text_color'],
            default_settings['font_family'], default_settings['banner_offset_x'],
            default_settings['banner_offset_y'], default_settings['avatar_offset_x'],
            default_settings['avatar_offset_y'], default_settings['text_offset_x'],
            default_settings['text_offset_y'], default_settings['send_gif_as_is'],
            default_settings['send_banner_as_is'], default_settings['welcome_text_size'],
            default_settings['username_text_size'],
            default_settings['use_goodbye_image'], default_settings['goodbye_text'],
            default_settings['goodbye_text_color'], default_settings['goodbye_profile_position'],
            default_settings['goodbye_font_family'], default_settings['goodbye_banner_url'],
            default_settings['goodbye_banner_offset_x'], default_settings['goodbye_banner_offset_y'],
            default_settings['goodbye_avatar_offset_x'], default_settings['goodbye_avatar_offset_y'],
            default_settings['goodbye_text_offset_x'], default_settings['goodbye_text_offset_y'],
            default_settings['goodbye_send_gif_as_is'], default_settings['goodbye_send_banner_as_is'],
            default_settings['welcome_text_bold'], default_settings['welcome_text_italic'], default_settings['welcome_text_underline'],
            default_settings['username_text_bold'], default_settings['username_text_italic'], default_settings['username_text_underline'],
            default_settings['goodbye_text_bold'], default_settings['goodbye_text_italic'], default_settings['goodbye_text_underline'],
            default_settings['goodbye_username_text_bold'], default_settings['goodbye_username_text_italic'], default_settings['goodbye_username_text_underline'],
            default_settings['google_font_family'], default_settings['custom_font_path'], default_settings['avatar_shape'],
            default_settings['goodbye_avatar_shape'],
            default_settings['avatar_border_enabled'], default_settings['avatar_border_width'],
            default_settings['avatar_border_color'],
            default_settings['goodbye_avatar_border_enabled'], default_settings['goodbye_avatar_border_width'],
            default_settings['goodbye_avatar_border_color'],
            default_settings['avatar_size'], default_settings['goodbye_avatar_size'],
            default_settings['goodbye_welcome_text_size'], default_settings['goodbye_username_text_size']
        ))
        conn.commit()
        # Convert integer (0/1) to boolean for boolean fields in default settings
        boolean_fields = [
            'music_auto_delete', 'music_shuffle', 'music_repeat',
            'welcome_enabled', 'goodbye_enabled', 'auto_role_enabled', 'use_image',
            'send_gif_as_is', 'send_banner_as_is', 'use_goodbye_image',
            'goodbye_send_gif_as_is', 'goodbye_send_banner_as_is',
            'welcome_text_bold', 'welcome_text_italic', 'welcome_text_underline',
            'username_text_bold', 'username_text_italic', 'username_text_underline',
            'goodbye_text_bold', 'goodbye_text_italic', 'goodbye_text_underline',
            'goodbye_username_text_bold', 'goodbye_username_text_italic', 'goodbye_username_text_underline',
            'avatar_border_enabled', 'goodbye_avatar_border_enabled'
        ]
        for field in boolean_fields:
            if field in default_settings:
                default_settings[field] = bool(default_settings[field])
        return default_settings

    result = dict(row)
    # Convert channel IDs to strings to preserve large Discord Snowflake IDs
    # JavaScript Number can't safely handle 18+ digit integers
    if result.get('welcome_channel_id'):
        result['welcome_channel_id'] = str(result['welcome_channel_id'])
    if result.get('goodbye_channel_id'):
        result['goodbye_channel_id'] = str(result['goodbye_channel_id'])
    if result.get('auto_role_id'):
        result['auto_role_id'] = str(result['auto_role_id'])
    # Parse auto_role_ids (comma-separated string to array)
    if result.get('auto_role_ids'):
        role_ids_str = result['auto_role_ids']
        if role_ids_str and role_ids_str.strip():
            result['auto_role_ids'] = [r.strip() for r in role_ids_str.split(',') if r.strip()]
        else:
            result['auto_role_ids'] = []
    else:
        result['auto_role_ids'] = []
    if result.get('moderation_log_channel_id'):
        result['moderation_log_channel_id'] = str(result['moderation_log_channel_id'])
    if result.get('music_channel_id'):
        result['music_channel_id'] = str(result['music_channel_id'])
    if result.get('level_up_channel_id'):
        result['level_up_channel_id'] = str(result['level_up_channel_id'])

    # Convert integer (0/1) to boolean for boolean fields
    boolean_fields = [
        'music_auto_delete', 'music_shuffle', 'music_repeat',
        'welcome_enabled', 'goodbye_enabled', 'auto_role_enabled', 'use_image',
        'send_gif_as_is', 'send_banner_as_is', 'use_goodbye_image',
        'goodbye_send_gif_as_is', 'goodbye_send_banner_as_is',
        'welcome_text_bold', 'welcome_text_italic', 'welcome_text_underline',
        'username_text_bold', 'username_text_italic', 'username_text_underline',
        'goodbye_text_bold', 'goodbye_text_italic', 'goodbye_text_underline',
        'goodbye_username_text_bold', 'goodbye_username_text_italic', 'goodbye_username_text_underline',
        'avatar_border_enabled', 'goodbye_avatar_border_enabled'
    ]
    for field in boolean_fields:
        if field in result:
            result[field] = bool(result[field])

    return result


def update_guild_settings(guild_id: int, settings: Dict[str, Any]) -> bool:
    """Update guild settings."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Build dynamic UPDATE query based on provided settings
        allowed_fields = [
            'music_auto_delete', 'music_default_volume', 'music_shuffle', 'music_repeat', 'music_channel_id', 'auto_disconnect_time',
            'welcome_channel_id', 'welcome_message', 'welcome_enabled',
            'goodbye_channel_id', 'goodbye_message', 'goodbye_enabled',
            'auto_role_enabled', 'auto_role_id', 'auto_role_ids', 'moderation_log_channel_id', 'prefix',
            # Welcome Image settings
            'use_image', 'banner_url', 'welcome_text', 'profile_position',
            'text_color', 'font_family', 'banner_offset_x', 'banner_offset_y', 'avatar_offset_x', 'avatar_offset_y',
            'text_offset_x', 'text_offset_y', 'send_gif_as_is', 'send_banner_as_is',
            'welcome_text_size', 'username_text_size', 'avatar_size',
            # Goodbye Image settings
            'use_goodbye_image', 'goodbye_text', 'goodbye_text_color', 'goodbye_profile_position',
            'goodbye_font_family', 'goodbye_banner_url', 'goodbye_banner_offset_x', 'goodbye_banner_offset_y',
            'goodbye_avatar_offset_x', 'goodbye_avatar_offset_y', 'goodbye_text_offset_x', 'goodbye_text_offset_y',
            'goodbye_send_gif_as_is', 'goodbye_send_banner_as_is',
            # Text style fields
            'welcome_text_bold', 'welcome_text_italic', 'welcome_text_underline',
            'username_text_bold', 'username_text_italic', 'username_text_underline',
            'goodbye_text_bold', 'goodbye_text_italic', 'goodbye_text_underline',
            'goodbye_username_text_bold', 'goodbye_username_text_italic', 'goodbye_username_text_underline',
            # Text size fields
            'goodbye_welcome_text_size', 'goodbye_username_text_size',
            # Font fields
            'google_font_family', 'custom_font_path',
            # Avatar shape
            'avatar_shape', 'goodbye_avatar_shape',
            # Avatar border
            'avatar_border_enabled', 'avatar_border_width', 'avatar_border_color',
            'goodbye_avatar_border_enabled', 'goodbye_avatar_border_width', 'goodbye_avatar_border_color',
            # Avatar size
            'avatar_size', 'goodbye_avatar_size'
        ]

        # Fields that should be stored as integers (channel IDs, role IDs)
        int_fields = {'welcome_channel_id', 'goodbye_channel_id', 'auto_role_id',
                      'moderation_log_channel_id', 'music_channel_id', 'auto_disconnect_time', 'level_up_channel_id'}
        # Boolean fields that need to be converted to integers (1/0)
        bool_fields = {'welcome_enabled', 'goodbye_enabled', 'auto_role_enabled', 'use_image',
                       'send_gif_as_is', 'send_banner_as_is', 'use_goodbye_image',
                       'goodbye_send_gif_as_is', 'goodbye_send_banner_as_is',
                       'music_auto_delete', 'music_shuffle', 'music_repeat',
                       # Text style boolean fields
                       'welcome_text_bold', 'welcome_text_italic', 'welcome_text_underline',
                       'username_text_bold', 'username_text_italic', 'username_text_underline',
                       'goodbye_text_bold', 'goodbye_text_italic', 'goodbye_text_underline',
                       'goodbye_username_text_bold', 'goodbye_username_text_italic', 'goodbye_username_text_underline',
                       # Avatar border
                       'avatar_border_enabled', 'goodbye_avatar_border_enabled'
                       }

        updates = []
        values = []
        for field in allowed_fields:
            if field in settings and settings[field] is not None:
                updates.append(f"{field} = ?")
                # Convert boolean to int (1/0) for SQLite
                if field in bool_fields:
                    value = 1 if settings[field] else 0
                # Convert auto_role_ids array to comma-separated string
                elif field == 'auto_role_ids' and isinstance(settings[field], list):
                    value = ','.join(str(v) for v in settings[field])
                # Convert channel/role IDs to int for database storage
                elif field in int_fields and settings[field]:
                    value = int(settings[field])
                else:
                    value = settings[field]
                values.append(value)

        if updates:
            values.append(guild_id)
            query = f"UPDATE guild_settings SET {', '.join(updates)} WHERE guild_id = ?"
            cursor.execute(query, values)
            conn.commit()
            return True

        return False

    except sqlite3.Error as e:
        print(f"Error updating guild settings: {e}")
        conn.rollback()
        return False


# ============================================================================
# CHATBOT
# ============================================================================

def get_chatbot_settings(guild_id: int) -> Dict[str, Any]:
    """Get chatbot settings for a guild."""
    import json

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM chatbot_settings WHERE guild_id = ?', (guild_id,))
    row = cursor.fetchone()

    if row is None:
        return {
            'guild_id': guild_id,
            'enabled': False,
            'model_name': 'llama-3.3-70b-versatile',
            'max_history': 10,
            'system_prompt': '',  # Empty - let user decide
            'temperature': 0.7,
            'enabled_channels': [],
            'api_key': None
        }

    result = dict(row)

    # Parse enabled_channels from JSON to list of strings
    if result.get('enabled_channels'):
        try:
            channels = json.loads(result['enabled_channels'])
            # Convert channel IDs to strings to avoid JavaScript precision loss
            result['enabled_channels'] = [str(ch) for ch in channels]
        except (json.JSONDecodeError, TypeError):
            result['enabled_channels'] = []
    else:
        result['enabled_channels'] = []

    # Return system_prompt as-is (empty string means user wants to use AI default behavior)
    if 'system_prompt' not in result:
        result['system_prompt'] = ''

    return result


def save_chatbot_settings(guild_id: int, settings: Dict[str, Any]) -> bool:
    """Save chatbot settings for a guild."""
    import json

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Handle enabled_channels - convert from array of strings to array of ints, then JSON
        enabled_channels = settings.get('enabled_channels', [])
        if enabled_channels and isinstance(enabled_channels, list):
            # Convert string IDs to integers for storage
            enabled_channels_int = [int(ch) for ch in enabled_channels if ch]
            enabled_channels_json = json.dumps(enabled_channels_int)
        else:
            enabled_channels_json = None

        # Handle system_prompt - ensure empty string is saved (not None)
        system_prompt = settings.get('system_prompt', '')
        if system_prompt is None:
            system_prompt = ''

        cursor.execute('''
            INSERT OR REPLACE INTO chatbot_settings
            (guild_id, enabled, model_name, max_history, system_prompt, temperature, enabled_channels, api_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            guild_id,
            settings.get('enabled', False),
            settings.get('model_name', 'llama-3.3-70b-versatile'),
            settings.get('max_history', 10),
            system_prompt,
            settings.get('temperature', 0.7),
            enabled_channels_json,
            settings.get('api_key')
        ))
        conn.commit()
        print(f"[DEBUG] Saved chatbot settings for guild {guild_id}, system_prompt: '{system_prompt}'")
        return True

    except sqlite3.Error as e:
        print(f"Error saving chatbot settings: {e}")
        conn.rollback()
        return False


def toggle_chatbot(guild_id: int, enabled: bool) -> bool:
    """Toggle chatbot enabled status."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO chatbot_settings (guild_id, enabled)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET enabled = ?
        ''', (guild_id, enabled, enabled))
        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Error toggling chatbot: {e}")
        conn.rollback()
        return False


def get_chat_history(guild_id: int, channel_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Get chat history for a channel."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT user_id, role, content, timestamp
        FROM chat_history
        WHERE guild_id = ? AND channel_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (guild_id, channel_id, limit))

    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def add_chat_message(guild_id: int, channel_id: int, user_id: int, role: str, content: str) -> bool:
    """Add a message to chat history."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO chat_history (guild_id, channel_id, user_id, role, content)
            VALUES (?, ?, ?, ?, ?)
        ''', (guild_id, channel_id, user_id, role, content))
        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Error adding chat message: {e}")
        conn.rollback()
        return False


def clear_chat_history(guild_id: int, channel_id: int) -> bool:
    """Clear chat history for a channel."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            DELETE FROM chat_history
            WHERE guild_id = ? AND channel_id = ?
        ''', (guild_id, channel_id))
        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Error clearing chat history: {e}")
        conn.rollback()
        return False


# ============================================================================
# LEVELING
# ============================================================================

def get_leveling_settings(guild_id: int) -> Dict[str, Any]:
    """Get leveling settings for a guild."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM leveling_settings WHERE guild_id = ?', (guild_id,))
    row = cursor.fetchone()

    if row is None:
        return {
            'guild_id': guild_id,
            'enabled': False,
            'xp_per_message': 10,
            'xp_per_minute': 60.0,
            'cooldown_seconds': 60,
            'level_up_announcements': True,
            'level_up_channel_id': None,
            'xp_multiplier': 1.0,
            'min_message_length': 0
        }

    result = dict(row)
    # Convert channel ID to string for JavaScript compatibility (Discord Snowflake ID)
    if result.get('level_up_channel_id'):
        result['level_up_channel_id'] = str(result['level_up_channel_id'])
    return result


def set_leveling_settings(guild_id: int, settings: Dict[str, Any]) -> bool:
    """Save leveling settings for a guild."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT OR REPLACE INTO leveling_settings
            (guild_id, enabled, xp_per_message, xp_per_minute, cooldown_seconds,
             level_up_announcements, level_up_channel_id, xp_multiplier, min_message_length)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            guild_id,
            settings.get('enabled', False),
            settings.get('xp_per_message', 10),
            settings.get('xp_per_minute', 60.0),
            settings.get('cooldown_seconds', 60),
            settings.get('level_up_announcements', True),
            settings.get('level_up_channel_id'),
            settings.get('xp_multiplier', 1.0),
            settings.get('min_message_length', 0)
        ))
        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Error saving leveling settings: {e}")
        conn.rollback()
        return False


def toggle_leveling(guild_id: int, enabled: bool) -> bool:
    """Toggle leveling enabled status."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO leveling_settings (guild_id, enabled)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET enabled = ?
        ''', (guild_id, enabled, enabled))
        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Error toggling leveling: {e}")
        conn.rollback()
        return False


def get_user_xp(guild_id: int, user_id: int) -> Dict[str, Any]:
    """Get user XP and level."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM user_xp WHERE guild_id = ? AND user_id = ?', (guild_id, user_id))
    row = cursor.fetchone()

    if row is None:
        return {
            'guild_id': guild_id,
            'user_id': user_id,
            'xp': 0,
            'level': 1,
            'message_count': 0,
            'total_xp': 0,
            'last_xp_gain': None
        }

    return dict(row)


def calculate_required_xp(level: int) -> int:
    """
    Calculate XP required for a given level.
    Level 1 -> 2: 150 XP
    Level 2 -> 3: 200 XP (150 + 50)
    Level 3 -> 4: 250 XP (150 + 50*2)
    Level n -> n+1: 150 + (n-1)*50
    """
    if level <= 1:
        return 150
    return 150 + (level - 1) * 50


def add_user_xp(guild_id: int, user_id: int, xp_amount: int) -> Tuple[bool, int, int]:
    """
    Add XP to a user.
    Returns (leveled_up, new_level, new_xp).
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Get current user data
        current = get_user_xp(guild_id, user_id)
        current_xp = current['xp']
        current_level = current['level']
        total_xp = current['total_xp']

        # Add XP
        new_xp = current_xp + xp_amount
        new_total_xp = total_xp + xp_amount
        new_level = current_level

        # Check for level up
        required_xp = calculate_required_xp(new_level)
        leveled_up = False

        while new_xp >= required_xp:
            new_xp -= required_xp
            new_level += 1
            required_xp = calculate_required_xp(new_level)
            leveled_up = True

        # Update database
        cursor.execute('''
            INSERT OR REPLACE INTO user_xp (guild_id, user_id, xp, level, total_xp)
            VALUES (?, ?, ?, ?, ?)
        ''', (guild_id, user_id, new_xp, new_level, new_total_xp))
        conn.commit()

        return leveled_up, new_level, new_xp

    except sqlite3.Error as e:
        print(f"Error adding user XP: {e}")
        conn.rollback()
        return False, current_level, current_xp


def level_up_user_with_xp(guild_id: int, user_id: int, current_level: int, xp_to_add: int) -> int:
    """
    Level up a user manually.
    Returns new level.
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        leveled_up, new_level, new_xp = add_user_xp(guild_id, user_id, xp_to_add)
        return new_level

    except Exception as e:
        print(f"Error leveling up user: {e}")
        return current_level


def update_message_count(guild_id: int, user_id: int) -> bool:
    """Increment user's message count."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO user_xp (guild_id, user_id, message_count)
            VALUES (?, ?, 1)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET message_count = message_count + 1
        ''', (guild_id, user_id))
        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Error updating message count: {e}")
        conn.rollback()
        return False


def get_user_rank(guild_id: int, user_id: int) -> int:
    """Get user's rank position in the guild leaderboard."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Get user's total XP and level
        cursor.execute('''
            SELECT total_xp, level FROM user_xp
            WHERE guild_id = ? AND user_id = ?
        ''', (guild_id, user_id))
        row = cursor.fetchone()

        if row is None:
            return 0

        user_total_xp = row['total_xp']
        user_level = row['level']

        # Count users with higher total XP or same XP but higher level
        cursor.execute('''
            SELECT COUNT(*) as rank
            FROM user_xp
            WHERE guild_id = ?
            AND (total_xp > ? OR (total_xp = ? AND level > ?))
        ''', (guild_id, user_total_xp, user_total_xp, user_level))

        return cursor.fetchone()['rank'] + 1

    except sqlite3.Error as e:
        print(f"Error getting user rank: {e}")
        return 0


def get_guild_leaderboard(guild_id: int, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
    """Get top users by level and XP."""
    conn = get_connection()
    cursor = conn.cursor()

    # Use GROUP BY to avoid duplicate user_ids
    cursor.execute('''
        SELECT user_id, MAX(xp) as xp, MAX(level) as level, MAX(message_count) as message_count, MAX(total_xp) as total_xp
        FROM user_xp
        WHERE guild_id = ?
        GROUP BY user_id
        ORDER BY level DESC, xp DESC
        LIMIT ? OFFSET ?
    ''', (guild_id, limit, offset))

    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def get_all_guild_users_xp(guild_id: int) -> List[Dict[str, Any]]:
    """Get all users XP data for a guild (no pagination)."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT user_id, xp, level, message_count, total_xp
        FROM user_xp
        WHERE guild_id = ?
    ''', (guild_id,))

    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def get_all_level_roles_below(guild_id: int, max_level: int) -> List[int]:
    """Get all role IDs for levels below or equal to max_level."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT role_id, stack
        FROM level_roles
        WHERE guild_id = ? AND level <= ?
        ORDER BY level DESC
    ''', (guild_id, max_level))

    rows = cursor.fetchall()

    # Return only stacking roles or the highest non-stacking role
    stacking_roles = [row['role_id'] for row in rows if row['stack']]
    non_stacking = [row for row in rows if not row['stack']]

    if non_stacking:
        # Get only the highest level non-stacking role
        stacking_roles.append(non_stacking[0]['role_id'])

    return stacking_roles


def get_level_roles(guild_id: int) -> List[Dict[str, Any]]:
    """Get all level role rewards for a guild."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, level, role_id, stack
        FROM level_roles
        WHERE guild_id = ?
        ORDER BY level ASC
    ''', (guild_id,))

    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def add_level_role(guild_id: int, level: int, role_id: int, stack: bool = False) -> bool:
    """Add a level role reward."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT OR REPLACE INTO level_roles (guild_id, level, role_id, stack)
            VALUES (?, ?, ?, ?)
        ''', (guild_id, level, role_id, stack))
        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Error adding level role: {e}")
        conn.rollback()
        return False


def remove_level_role(guild_id: int, level: int, role_id: int) -> bool:
    """Remove a level role reward."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            DELETE FROM level_roles
            WHERE guild_id = ? AND level = ? AND role_id = ?
        ''', (guild_id, level, role_id))
        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Error removing level role: {e}")
        conn.rollback()
        return False


def update_level_role(guild_id: int, old_level: int, old_role_id: int,
                      new_level: int, new_role_id: int, stack: bool = False) -> bool:
    """Update a level role reward."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            UPDATE level_roles
            SET level = ?, role_id = ?, stack = ?
            WHERE guild_id = ? AND level = ? AND role_id = ?
        ''', (new_level, new_role_id, int(stack), guild_id, old_level, old_role_id))
        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Error updating level role: {e}")
        conn.rollback()
        return False


def get_xp_for_level(level: int, base_xp: int = 100, xp_increment: int = 50) -> int:
    """Get XP required for a specific level."""
    if level <= 1:
        return base_xp
    return base_xp + (level - 1) * xp_increment


# ============================================================================
# EXCLUDED ROLES (Roles that cannot gain XP)
# ============================================================================

def get_excluded_roles(guild_id: int) -> List[int]:
    """Get all excluded role IDs for a guild."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT role_id
        FROM excluded_roles
        WHERE guild_id = ?
    ''', (guild_id,))

    rows = cursor.fetchall()
    return [row['role_id'] for row in rows]


def add_excluded_role(guild_id: int, role_id: int) -> bool:
    """Add a role to the excluded roles list."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT OR IGNORE INTO excluded_roles (guild_id, role_id)
            VALUES (?, ?)
        ''', (guild_id, role_id))
        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Error adding excluded role: {e}")
        conn.rollback()
        return False


def remove_excluded_role(guild_id: int, role_id: int) -> bool:
    """Remove a role from the excluded roles list."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            DELETE FROM excluded_roles
            WHERE guild_id = ? AND role_id = ?
        ''', (guild_id, role_id))
        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Error removing excluded role: {e}")
        conn.rollback()
        return False


def is_user_excluded(guild_id: int, user_roles: List[int]) -> bool:
    """Check if a user should be excluded from XP (has any excluded role)."""
    excluded_roles = get_excluded_roles(guild_id)
    if not excluded_roles:
        return False
    return any(role_id in excluded_roles for role_id in user_roles)


def reset_user_xp(guild_id: int, user_id: int) -> bool:
    """Reset a user's XP to level 1."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT OR REPLACE INTO user_xp (guild_id, user_id, xp, level, total_xp, message_count)
            VALUES (?, ?, 0, 1, 0, 0)
        ''', (guild_id, user_id))
        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Error resetting user XP: {e}")
        conn.rollback()
        return False


def set_user_xp(guild_id: int, user_id: int, level: int, xp: int) -> bool:
    """Set a user's level and XP directly."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Check if user exists
        cursor.execute('''
            SELECT message_count FROM user_xp WHERE guild_id = ? AND user_id = ?
        ''', (guild_id, user_id))
        row = cursor.fetchone()

        # Recalculate total_xp based on new level and xp
        total_xp = sum(get_xp_for_level(l) for l in range(1, level)) + xp

        if row:
            # Update existing user, preserve message_count
            message_count = row['message_count'] or 0
            cursor.execute('''
                UPDATE user_xp
                SET xp = ?, level = ?, total_xp = ?, message_count = ?
                WHERE guild_id = ? AND user_id = ?
            ''', (xp, level, total_xp, message_count, guild_id, user_id))
        else:
            # Insert new user
            cursor.execute('''
                INSERT INTO user_xp (guild_id, user_id, xp, level, total_xp, message_count)
                VALUES (?, ?, ?, ?, ?, 0)
            ''', (guild_id, user_id, xp, level, total_xp))

        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Error setting user XP: {e}")
        conn.rollback()
        return False


def recalculate_all_user_levels(guild_id: int) -> bool:
    """Recalculate all user levels based on total XP."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT user_id, total_xp FROM user_xp WHERE guild_id = ?
        ''', (guild_id,))

        users = cursor.fetchall()

        for user in users:
            user_id = user['user_id']
            total_xp = user['total_xp']

            # Calculate level from total XP
            level = 1
            remaining_xp = total_xp

            while remaining_xp >= calculate_required_xp(level):
                remaining_xp -= calculate_required_xp(level)
                level += 1

            # Update user
            cursor.execute('''
                UPDATE user_xp SET level = ?, xp = ?
                WHERE guild_id = ? AND user_id = ?
            ''', (level, remaining_xp, guild_id, user_id))

        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Error recalculating user levels: {e}")
        conn.rollback()
        return False


# ============================================================================
# WELCOME
# ============================================================================

def get_welcome_roles(guild_id: int) -> List[int]:
    """Get welcome role IDs for a guild."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT role_id FROM welcome_roles WHERE guild_id = ?', (guild_id,))
    rows = cursor.fetchall()
    return [row['role_id'] for row in rows]


def add_welcome_role(guild_id: int, role_id: int) -> bool:
    """Add a welcome role."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT OR IGNORE INTO welcome_roles (guild_id, role_id)
            VALUES (?, ?)
        ''', (guild_id, role_id))
        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Error adding welcome role: {e}")
        conn.rollback()
        return False


def remove_welcome_role(guild_id: int, role_id: int) -> bool:
    """Remove a welcome role."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            DELETE FROM welcome_roles WHERE guild_id = ? AND role_id = ?
        ''', (guild_id, role_id))
        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Error removing welcome role: {e}")
        conn.rollback()
        return False


# ============================================================================
# MODERATION
# ============================================================================

def get_moderation_roles(guild_id: int) -> List[str]:
    """Get moderation role IDs for a guild. Returns strings for JavaScript compatibility."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT role_id FROM moderation_roles WHERE guild_id = ?', (guild_id,))
    rows = cursor.fetchall()
    # Convert to strings for JavaScript (Discord Snowflake IDs)
    return [str(row['role_id']) for row in rows]


def add_moderation_role(guild_id: int, role_id: int, permissions: str = 'all') -> bool:
    """Add a moderation role."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if IS_POSTGRES:
            cursor.execute('''
                INSERT INTO moderation_roles (guild_id, role_id, permissions)
                VALUES (%s, %s, %s)
                ON CONFLICT (guild_id, role_id) DO UPDATE SET permissions = EXCLUDED.permissions
            ''', (guild_id, role_id, permissions))
        else:
            cursor.execute('''
                INSERT OR REPLACE INTO moderation_roles (guild_id, role_id, permissions)
                VALUES (?, ?, ?)
            ''', (guild_id, role_id, permissions))
        conn.commit()
        return True

    except DBError as e:
        print(f"Error adding moderation role: {e}")
        conn.rollback()
        return False


def remove_moderation_role(guild_id: int, role_id: int) -> bool:
    """Remove a moderation role."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            DELETE FROM moderation_roles WHERE guild_id = ? AND role_id = ?
        ''', (guild_id, role_id))
        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Error removing moderation role: {e}")
        conn.rollback()
        return False


def add_moderation_log(guild_id: int, moderator_id: int, user_id: int,
                       action: str, reason: str = None, duration: int = None) -> bool:
    """Add a moderation log entry."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO moderation_logs (guild_id, moderator_id, user_id, action, reason, duration)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (guild_id, moderator_id, user_id, action, reason, duration))
        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Error adding moderation log: {e}")
        conn.rollback()
        return False


def get_moderation_logs(guild_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent moderation logs for a guild."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, moderator_id, user_id, action, reason, duration, timestamp
        FROM moderation_logs
        WHERE guild_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (guild_id, limit))

    rows = cursor.fetchall()
    return [dict(row) for row in rows]


# ============================================================================
# AUDIT LOGS
# ============================================================================

def add_audit_log(guild_id: int, user_id: int, user_name: str, action: str, category: str, details: str = None) -> bool:
    """Add an audit log entry."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO audit_logs (guild_id, user_id, user_name, action, category, details)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (guild_id, user_id, user_name, action, category, details))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error adding audit log: {e}")
        conn.rollback()
        return False


def get_audit_logs(guild_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    """Get audit logs for a guild."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, guild_id, user_id, user_name, action, category, details, timestamp
        FROM audit_logs
        WHERE guild_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (guild_id, limit))

    rows = cursor.fetchall()
    return [dict(row) for row in rows]


# ============================================================================
# USER MUSIC GENRES (Per-user custom music genres)
# ============================================================================

def add_user_genre(user_id: int, genre_name: str, search_query: str, emoji: str = '🎵') -> bool:
    """Add a custom music genre for a user."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if IS_POSTGRES:
            cursor.execute('''
                INSERT INTO user_music_genres (user_id, genre_name, search_query, emoji)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, genre_name) DO UPDATE SET 
                    search_query = EXCLUDED.search_query,
                    emoji = EXCLUDED.emoji
            ''', (user_id, genre_name, search_query, emoji))
        else:
            cursor.execute('''
                INSERT OR REPLACE INTO user_music_genres (user_id, genre_name, search_query, emoji)
                VALUES (?, ?, ?, ?)
            ''', (user_id, genre_name, search_query, emoji))
        conn.commit()
        return True
    except DBError as e:
        print(f"Error adding user genre: {e}")
        conn.rollback()
        return False


def get_user_genres(user_id: int) -> List[Dict[str, Any]]:
    """Get all custom music genres for a user."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, user_id, genre_name, search_query, emoji, created_at
        FROM user_music_genres
        WHERE user_id = ?
        ORDER BY created_at DESC
    ''', (user_id,))

    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def delete_user_genre(user_id: int, genre_id: int) -> bool:
    """Delete a custom music genre for a user."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            DELETE FROM user_music_genres
            WHERE id = ? AND user_id = ?
        ''', (genre_id, user_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error deleting user genre: {e}")
        conn.rollback()
        return False


def get_user_genre_by_id(user_id: int, genre_id: int) -> Optional[Dict[str, Any]]:
    """Get a specific custom music genre by ID."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, user_id, genre_name, search_query, emoji, created_at
        FROM user_music_genres
        WHERE id = ? AND user_id = ?
    ''', (genre_id, user_id))

    row = cursor.fetchone()
    return dict(row) if row else None


def get_all_genres_for_user(user_id: int) -> Dict[str, Any]:
    """
    Get all genres (default + user custom) for a user.
    Returns dict with 'default' list and 'custom' list.
    """
    # Default genres (hardcoded as in music.py)
    default_genres = [
        {"value": "pop", "label": "Pop", "emoji": "🎤", "description": "Top pop hits"},
        {"value": "rock", "label": "Rock", "emoji": "🎸", "description": "Classic & modern rock"},
        {"value": "hip-hop", "label": "Hip-Hop", "emoji": "🎧", "description": "Hip-hop & rap"},
        {"value": "edm", "label": "EDM", "emoji": "🎹", "description": "Electronic dance music"},
        {"value": "jazz", "label": "Jazz", "emoji": "🎷", "description": "Jazz classics"},
        {"value": "classical", "label": "Classical", "emoji": "🎻", "description": "Classical music"},
        {"value": "k-pop", "label": "K-Pop", "emoji": "🌟", "description": "Korean pop"},
        {"value": "rnb", "label": "R&B", "emoji": "🎤", "description": "R&B soul"},
        {"value": "country", "label": "Country", "emoji": "🤠", "description": "Country hits"},
        {"value": "lofi", "label": "Lo-Fi", "emoji": "☕", "description": "Lo-fi beats"},
        {"value": "indie", "label": "Indie", "emoji": "🌿", "description": "Indie music"},
    ]

    # Get user's custom genres
    custom_genres = get_user_genres(user_id)

    return {
        'default': default_genres,
        'custom': custom_genres
    }

# ============================================================================
# CHATBOT
# ============================================================================

def get_chatbot_settings(guild_id: int) -> Dict[str, Any]:
    """Get chatbot settings for a guild."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM chatbot_settings WHERE guild_id = %s', (guild_id,))
    row = cursor.fetchone()

    if row is None:
        return {
            'guild_id': guild_id,
            'enabled': False,
            'model_name': 'llama-3.3-70b-versatile',
            'max_history': 10,
            'system_prompt': '',
            'temperature': 0.7,
            'enabled_channels': [],
            'api_key': None
        }

    result = dict(row)

    # Parse enabled_channels from JSON to list of strings
    if result.get('enabled_channels'):
        try:
            channels = json.loads(result['enabled_channels'])
            result['enabled_channels'] = [str(ch) for ch in channels]
        except (json.JSONDecodeError, TypeError):
            result['enabled_channels'] = []
    else:
        result['enabled_channels'] = []

    if 'system_prompt' not in result or result['system_prompt'] is None:
        result['system_prompt'] = ''

    return result


def save_chatbot_settings(guild_id: int, settings: Dict[str, Any]) -> bool:
    """Save chatbot settings for a guild."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        enabled_channels = settings.get('enabled_channels', [])
        if enabled_channels and isinstance(enabled_channels, list):
            enabled_channels_int = [int(ch) for ch in enabled_channels if ch]
            enabled_channels_json = json.dumps(enabled_channels_int)
        else:
            enabled_channels_json = None

        system_prompt = settings.get('system_prompt', '')
        if system_prompt is None:
            system_prompt = ''

        cursor.execute('''
            INSERT INTO chatbot_settings
            (guild_id, enabled, model_name, max_history, system_prompt, temperature, enabled_channels, api_key)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (guild_id) DO UPDATE SET
                enabled = EXCLUDED.enabled,
                model_name = EXCLUDED.model_name,
                max_history = EXCLUDED.max_history,
                system_prompt = EXCLUDED.system_prompt,
                temperature = EXCLUDED.temperature,
                enabled_channels = EXCLUDED.enabled_channels,
                api_key = EXCLUDED.api_key
        ''', (
            guild_id,
            settings.get('enabled', False),
            settings.get('model_name', 'llama-3.3-70b-versatile'),
            settings.get('max_history', 10),
            system_prompt,
            settings.get('temperature', 0.7),
            enabled_channels_json,
            settings.get('api_key')
        ))
        conn.commit()
        return True

    except psycopg2.Error as e:
        print(f"Error saving chatbot settings: {e}")
        conn.rollback()
        return False


def toggle_chatbot(guild_id: int, enabled: bool) -> bool:
    """Toggle chatbot enabled status."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO chatbot_settings (guild_id, enabled)
            VALUES (%s, %s)
            ON CONFLICT(guild_id) DO UPDATE SET enabled = %s
        ''', (guild_id, enabled, enabled))
        conn.commit()
        return True

    except psycopg2.Error as e:
        print(f"Error toggling chatbot: {e}")
        conn.rollback()
        return False


def get_chat_history(guild_id: int, channel_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Get chat history for a channel."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT user_id, role, content, timestamp
        FROM chat_history
        WHERE guild_id = %s AND channel_id = %s
        ORDER BY timestamp DESC
        LIMIT %s
    ''', (guild_id, channel_id, limit))

    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def add_chat_message(guild_id: int, channel_id: int, user_id: int, role: str, content: str) -> bool:
    """Add a message to chat history."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO chat_history (guild_id, channel_id, user_id, role, content)
            VALUES (%s, %s, %s, %s, %s)
        ''', (guild_id, channel_id, user_id, role, content))
        conn.commit()
        return True

    except psycopg2.Error as e:
        print(f"Error adding chat message: {e}")
        conn.rollback()
        return False


def clear_chat_history(guild_id: int, channel_id: int) -> bool:
    """Clear chat history for a channel."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            DELETE FROM chat_history
            WHERE guild_id = %s AND channel_id = %s
        ''', (guild_id, channel_id))
        conn.commit()
        return True

    except psycopg2.Error as e:
        print(f"Error clearing chat history: {e}")
        conn.rollback()
        return False


# ============================================================================
# LEVELING
# ============================================================================

def get_leveling_settings(guild_id: int) -> Dict[str, Any]:
    """Get leveling settings for a guild."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM leveling_settings WHERE guild_id = %s', (guild_id,))
    row = cursor.fetchone()

    if row is None:
        return {
            'guild_id': guild_id,
            'enabled': False,
            'xp_per_message': 10,
            'xp_per_minute': 60.0,
            'cooldown_seconds': 60,
            'level_up_announcements': True,
            'level_up_channel_id': None,
            'xp_multiplier': 1.0,
            'min_message_length': 0
        }

    result = dict(row)
    if result.get('level_up_channel_id'):
        result['level_up_channel_id'] = str(result['level_up_channel_id'])
    return result


def set_leveling_settings(guild_id: int, settings: Dict[str, Any]) -> bool:
    """Save leveling settings for a guild."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO leveling_settings
            (guild_id, enabled, xp_per_message, xp_per_minute, cooldown_seconds,
             level_up_announcements, level_up_channel_id, xp_multiplier, min_message_length)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (guild_id) DO UPDATE SET
                enabled = EXCLUDED.enabled,
                xp_per_message = EXCLUDED.xp_per_message,
                xp_per_minute = EXCLUDED.xp_per_minute,
                cooldown_seconds = EXCLUDED.cooldown_seconds,
                level_up_announcements = EXCLUDED.level_up_announcements,
                level_up_channel_id = EXCLUDED.level_up_channel_id,
                xp_multiplier = EXCLUDED.xp_multiplier,
                min_message_length = EXCLUDED.min_message_length
        ''', (
            guild_id,
            settings.get('enabled', False),
            settings.get('xp_per_message', 10),
            settings.get('xp_per_minute', 60.0),
            settings.get('cooldown_seconds', 60),
            settings.get('level_up_announcements', True),
            settings.get('level_up_channel_id'),
            settings.get('xp_multiplier', 1.0),
            settings.get('min_message_length', 0)
        ))
        conn.commit()
        return True

    except psycopg2.Error as e:
        print(f"Error saving leveling settings: {e}")
        conn.rollback()
        return False


def toggle_leveling(guild_id: int, enabled: bool) -> bool:
    """Toggle leveling enabled status."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO leveling_settings (guild_id, enabled)
            VALUES (%s, %s)
            ON CONFLICT(guild_id) DO UPDATE SET enabled = %s
        ''', (guild_id, enabled, enabled))
        conn.commit()
        return True

    except psycopg2.Error as e:
        print(f"Error toggling leveling: {e}")
        conn.rollback()
        return False


def get_user_xp(guild_id: int, user_id: int) -> Dict[str, Any]:
    """Get user XP and level."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM user_xp WHERE guild_id = %s AND user_id = %s', (guild_id, user_id))
    row = cursor.fetchone()

    if row is None:
        return {
            'guild_id': guild_id,
            'user_id': user_id,
            'xp': 0,
            'level': 1,
            'message_count': 0,
            'total_xp': 0,
            'last_xp_gain': None
        }

    return dict(row)


def calculate_required_xp(level: int) -> int:
    """Calculate XP required for a given level."""
    if level <= 1:
        return 150
    return 150 + (level - 1) * 50


def add_user_xp(guild_id: int, user_id: int, xp_amount: int) -> Tuple[bool, int, int]:
    """Add XP to a user. Returns (leveled_up, new_level, new_xp)."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        current = get_user_xp(guild_id, user_id)
        current_xp = current['xp']
        current_level = current['level']
        total_xp = current['total_xp']

        new_xp = current_xp + xp_amount
        new_total_xp = total_xp + xp_amount
        new_level = current_level

        required_xp = calculate_required_xp(new_level)
        leveled_up = False

        while new_xp >= required_xp:
            new_xp -= required_xp
            new_level += 1
            required_xp = calculate_required_xp(new_level)
            leveled_up = True

        cursor.execute('''
            INSERT INTO user_xp (guild_id, user_id, xp, level, total_xp)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (guild_id, user_id) DO UPDATE SET
                xp = EXCLUDED.xp,
                level = EXCLUDED.level,
                total_xp = EXCLUDED.total_xp,
                last_xp_gain = CURRENT_TIMESTAMP
        ''', (guild_id, user_id, new_xp, new_level, new_total_xp))
        conn.commit()

        return leveled_up, new_level, new_xp

    except psycopg2.Error as e:
        print(f"Error adding user XP: {e}")
        conn.rollback()
        return False, current_level, current_xp


def level_up_user_with_xp(guild_id: int, user_id: int, current_level: int, xp_to_add: int) -> int:
    """Level up a user manually."""
    try:
        leveled_up, new_level, new_xp = add_user_xp(guild_id, user_id, xp_to_add)
        return new_level

    except Exception as e:
        print(f"Error leveling up user: {e}")
        return current_level


def update_message_count(guild_id: int, user_id: int) -> bool:
    """Increment user's message count."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO user_xp (guild_id, user_id, message_count)
            VALUES (%s, %s, 1)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET message_count = user_xp.message_count + 1
        ''', (guild_id, user_id))
        conn.commit()
        return True

    except psycopg2.Error as e:
        print(f"Error updating message count: {e}")
        conn.rollback()
        return False


def get_user_rank(guild_id: int, user_id: int) -> int:
    """Get user's rank position in the guild leaderboard."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT total_xp, level FROM user_xp
            WHERE guild_id = %s AND user_id = %s
        ''', (guild_id, user_id))
        row = cursor.fetchone()

        if row is None:
            return 0

        user_total_xp = row['total_xp']
        user_level = row['level']

        cursor.execute('''
            SELECT COUNT(*) as rank
            FROM user_xp
            WHERE guild_id = %s
            AND (total_xp > %s OR (total_xp = %s AND level > %s))
        ''', (guild_id, user_total_xp, user_total_xp, user_level))

        # RealDictCursor returns dict
        return cursor.fetchone()['rank'] + 1

    except psycopg2.Error as e:
        print(f"Error getting user rank: {e}")
        return 0


def get_guild_leaderboard(guild_id: int, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
    """Get top users by level and XP."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT user_id, MAX(xp) as xp, MAX(level) as level, MAX(message_count) as message_count, MAX(total_xp) as total_xp
        FROM user_xp
        WHERE guild_id = %s
        GROUP BY user_id
        ORDER BY level DESC, xp DESC
        LIMIT %s OFFSET %s
    ''', (guild_id, limit, offset))

    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def get_all_guild_users_xp(guild_id: int) -> List[Dict[str, Any]]:
    """Get all users XP data for a guild (no pagination)."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT user_id, xp, level, message_count, total_xp
        FROM user_xp
        WHERE guild_id = %s
    ''', (guild_id,))

    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def get_all_level_roles_below(guild_id: int, max_level: int) -> List[int]:
    """Get all role IDs for levels below or equal to max_level."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT role_id, stack
        FROM level_roles
        WHERE guild_id = %s AND level <= %s
        ORDER BY level DESC
    ''', (guild_id, max_level))

    rows = cursor.fetchall()

    stacking_roles = [row['role_id'] for row in rows if row['stack']]
    non_stacking = [row for row in rows if not row['stack']]

    if non_stacking:
        stacking_roles.append(non_stacking[0]['role_id'])

    return stacking_roles


def get_level_roles(guild_id: int) -> List[Dict[str, Any]]:
    """Get all level role rewards for a guild."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, level, role_id, stack
        FROM level_roles
        WHERE guild_id = %s
        ORDER BY level ASC
    ''', (guild_id,))

    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def add_level_role(guild_id: int, level: int, role_id: int, stack: bool = False) -> bool:
    """Add a level role reward."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO level_roles (guild_id, level, role_id, stack)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (guild_id, level, role_id) DO UPDATE SET stack = EXCLUDED.stack
        ''', (guild_id, level, role_id, stack))
        conn.commit()
        return True

    except psycopg2.Error as e:
        print(f"Error adding level role: {e}")
        conn.rollback()
        return False


def remove_level_role(guild_id: int, level: int, role_id: int) -> bool:
    """Remove a level role reward."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            DELETE FROM level_roles
            WHERE guild_id = %s AND level = %s AND role_id = %s
        ''', (guild_id, level, role_id))
        conn.commit()
        return True

    except psycopg2.Error as e:
        print(f"Error removing level role: {e}")
        conn.rollback()
        return False


def update_level_role(guild_id: int, old_level: int, old_role_id: int,
                      new_level: int, new_role_id: int, stack: bool = False) -> bool:
    """Update a level role reward."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            UPDATE level_roles
            SET level = %s, role_id = %s, stack = %s
            WHERE guild_id = %s AND level = %s AND role_id = %s
        ''', (new_level, new_role_id, stack, guild_id, old_level, old_role_id))
        conn.commit()
        return True

    except psycopg2.Error as e:
        print(f"Error updating level role: {e}")
        conn.rollback()
        return False


def get_xp_for_level(level: int, base_xp: int = 100, xp_increment: int = 50) -> int:
    """Get XP required for a specific level."""
    if level <= 1:
        return base_xp
    return base_xp + (level - 1) * xp_increment
