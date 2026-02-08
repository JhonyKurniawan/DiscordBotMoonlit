"""
Flask application for Discord Bot Dashboard
Web interface and API endpoints
"""

import os
import sys
import time
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify, session, redirect, send_from_directory, send_file
from flask_cors import CORS
from functools import wraps
import requests
from werkzeug.utils import secure_filename
from . import database as db

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Path to frontend dist folder
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend', 'dist')

# Load configuration
try:
    from config import (
        DISCORD_CLIENT_ID,
        DISCORD_CLIENT_SECRET,
        DASHBOARD_SECRET_KEY,
        DISCORD_REDIRECT_URI,
        DASHBOARD_BASE_URL,
        BOT_TOKEN
    )
    REDIRECT_URI = DISCORD_REDIRECT_URI
except ImportError:
    DISCORD_CLIENT_ID = os.environ.get('DISCORD_CLIENT_ID', '1466521449492648099')
    DISCORD_CLIENT_SECRET = os.environ.get('DISCORD_CLIENT_SECRET', '')
    DASHBOARD_SECRET_KEY = os.environ.get('DASHBOARD_SECRET_KEY', 'dev-secret-key-change-in-production')
    REDIRECT_URI = os.environ.get('REDIRECT_URI', 'http://localhost:5001/callback')
    BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN', '')
    DASHBOARD_BASE_URL = os.environ.get('DASHBOARD_BASE_URL', 'http://localhost:5001')

# Debug print
print(f'[DEBUG] CLIENT_ID={DISCORD_CLIENT_ID}')
print(f'[DEBUG] CLIENT_SECRET={DISCORD_CLIENT_SECRET[:10]}...{DISCORD_CLIENT_SECRET[-4:]}')
print(f'[DEBUG] REDIRECT_URI={REDIRECT_URI}')

# Create Flask app
app = Flask(__name__)
app.secret_key = DASHBOARD_SECRET_KEY or 'dev-secret-key-change-in-production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Enable CORS for frontend development and production
CORS(app, supports_credentials=True,
     origins=['http://localhost:5190', 'http://localhost:5174', 'https://moonlit-bot.my.id'],
     allow_headers=['Content-Type', 'Authorization'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])

# Discord API endpoints
DISCORD_API_BASE = 'https://discord.com/api/v10'
DISCORD_AUTH_URL = f'https://discord.com/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope=identify%20guilds'


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_discord_token():
    """Get stored Discord access token from session or header."""
    # First try session (for callback)
    token = session.get('discord_token')
    if token:
        return token

    # Then try Authorization header (from frontend)
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]

    return None


def get_discord_user():
    """Get current Discord user info."""
    if 'discord_user' in session:
        return session['discord_user']
    return None


def log_audit_action(guild_id, action, category, details=None):
    """Log an audit action for the dashboard."""
    user = get_discord_user()
    if user:
        db.add_audit_log(
            guild_id=guild_id,
            user_id=user.get('id', ''),
            user_name=user.get('username', 'Unknown'),
            action=action,
            category=category,
            details=details
        )


def require_login(f):
    """Decorator to require Discord login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_discord_token()
        if not token:
            return jsonify({'error': 'Login required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def get_user_guilds():
    """Get guilds for the logged-in user."""
    token = get_discord_token()
    if not token:
        return []

    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(f'{DISCORD_API_BASE}/users/@me/guilds', headers=headers)

    if response.status_code == 200:
        return response.json()
    return []


def can_manage_guild(guild):
    """Check if user can manage a guild (owner or admin permission)."""
    user = get_discord_user()
    if not user:
        return False

    # Check if owner
    if guild.get('owner') is True:
        return True

    # Check for administrator permission (0x8)
    permissions = int(guild.get('permissions', 0))
    return (permissions & 0x8) == 0x8


# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def serve_index():
    """Serve Vue frontend index page."""
    return send_from_directory(FRONTEND_DIST, 'index.html')


@app.route('/api/auth/discord')
def auth_discord():
    """Redirect to Discord OAuth2 login."""
    return redirect(DISCORD_AUTH_URL)


@app.route('/callback')
def callback():
    """Discord OAuth2 callback handler."""
    code = request.args.get('code')
    if not code:
        # This might be a callback from frontend (already has token), ignore
        return redirect('https://moonlit-bot.my.id/')

    print(f'[INFO] Callback received, REDIRECT_URI={REDIRECT_URI}')

    # Exchange code for token
    data = {
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.post(f'{DISCORD_API_BASE}/oauth2/token', data=data, headers=headers)

    print(f'[INFO] Token exchange status: {response.status_code}')

    if response.status_code != 200:
        print(f'[ERROR] Token exchange failed: {response.text}')
        return redirect('https://moonlit-bot.my.id/?error=token_exchange_failed')

    token_data = response.json()
    access_token = token_data.get('access_token')

    if not access_token:
        print(f'[ERROR] No access token in response: {token_data}')
        return redirect('https://moonlit-bot.my.id/?error=no_access_token')

    # Get user info
    headers = {'Authorization': f'Bearer {access_token}'}
    user_response = requests.get(f'{DISCORD_API_BASE}/users/@me', headers=headers)

    if user_response.status_code != 200:
        print(f'[ERROR] User fetch failed: {user_response.text}')
        return redirect('https://moonlit-bot.my.id/?error=user_fetch_failed')

    user_data = user_response.json()
    print(f'[INFO] Logged in user: {user_data.get("username")}')

    # Store in session for API calls
    session['discord_token'] = access_token
    session['discord_user'] = user_data

    # Redirect with token in URL for frontend to pick up
    from urllib.parse import urlencode
    params = urlencode({
        'token': access_token,
        'user': user_data.get('username'),
        'user_id': user_data.get('id'),
        'avatar': user_data.get('avatar', ''),
        'discriminator': user_data.get('discriminator', '0')
    })
    return redirect(f'https://moonlit-bot.my.id/callback?{params}')


# All other routes below...


@app.route('/api/auth/logout')
def logout():
    """Logout and clear session."""
    session.clear()
    return jsonify({'success': True})


@app.route('/api/auth/me')
def auth_me():
    """Get current user info."""
    user = get_discord_user()
    if not user:
        return jsonify({'error': 'Not logged in'}), 401
    return jsonify(user)


@app.route('/api/guilds')
@require_login
def api_guilds():
    """Get user's guilds - only guilds where the bot is present."""
    user_guilds = get_user_guilds()

    # Get bot's guilds
    bot_guilds = []
    try:
        headers = {'Authorization': f'Bot {BOT_TOKEN}'}
        response = requests.get(f'{DISCORD_API_BASE}/users/@me/guilds', headers=headers)
        if response.status_code == 200:
            bot_guilds = response.json()
    except Exception as e:
        print(f'[ERROR] Failed to get bot guilds: {e}')

    # Create set of bot guild IDs for quick lookup
    bot_guild_ids = {str(g['id']) for g in bot_guilds}

    # Filter to only manageable guilds where bot is present
    manageable = [g for g in user_guilds if can_manage_guild(g) and str(g['id']) in bot_guild_ids]
    return jsonify(manageable)


# ============================================================================
# GUILD SETTINGS API
# ============================================================================

@app.route('/api/guilds/<int:guild_id>/settings', methods=['GET'])
@require_login
def get_guild_settings(guild_id):
    """Get guild settings."""
    settings = db.get_guild_settings(guild_id)
    return jsonify(settings)


@app.route('/api/guilds/<int:guild_id>/settings', methods=['PUT'])
@require_login
def update_guild_settings_api(guild_id):
    """Update guild settings."""
    data = request.get_json()
    success = db.update_guild_settings(guild_id, data)

    if success:
        log_audit_action(guild_id, 'Updated guild settings', 'general')
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to update settings'}), 500


# Font upload directory
FONT_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'fonts', 'custom')
os.makedirs(FONT_UPLOAD_DIR, exist_ok=True)


@app.route('/api/guilds/<int:guild_id>/upload-font', methods=['POST'])
@require_login
def upload_font(guild_id):
    """Upload a custom font file for welcome/goodbye images."""
    if 'font' not in request.files:
        return jsonify({'error': 'No font file provided'}), 400

    file = request.files['font']
    if file.filename == '':
        return jsonify({'error': 'No font file selected'}), 400

    # Check file extension
    if not file.filename.lower().endswith(('.ttf', '.otf', '.woff', '.woff2')):
        return jsonify({'error': 'Invalid font file type. Only TTF, OTF, WOFF, WOFF2 files are allowed.'}), 400

    try:
        # Secure the filename
        filename = secure_filename(file.filename)
        # Add guild_id prefix to prevent conflicts
        safe_filename = f"guild_{guild_id}_{filename}"
        filepath = os.path.join(FONT_UPLOAD_DIR, safe_filename)

        # Save the file
        file.save(filepath)

        # Return the path that will be stored in database
        font_path = filepath
        return jsonify({
            'success': True,
            'font_path': font_path,
            'filename': filename
        })
    except Exception as e:
        print(f"Error uploading font: {e}")
        return jsonify({'error': 'Failed to upload font file'}), 500


# ============================================================================
# CHATBOT API
# ============================================================================

@app.route('/api/guilds/<int:guild_id>/chatbot', methods=['GET'])
@require_login
def get_chatbot_settings_api(guild_id):
    """Get chatbot settings."""
    settings = db.get_chatbot_settings(guild_id)
    return jsonify(settings)


@app.route('/api/guilds/<int:guild_id>/chatbot', methods=['POST'])
@require_login
def update_chatbot_settings_api(guild_id):
    """Update chatbot settings."""
    data = request.get_json()
    success = db.save_chatbot_settings(guild_id, data)

    if success:
        log_audit_action(guild_id, 'Updated chatbot settings', 'chatbot')
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to update settings'}), 500


@app.route('/api/guilds/<int:guild_id>/chatbot/toggle', methods=['POST'])
@require_login
def toggle_chatbot_api(guild_id):
    """Toggle chatbot enabled status."""
    data = request.get_json()
    enabled = data.get('enabled', False)
    success = db.toggle_chatbot(guild_id, enabled)

    if success:
        status = 'enabled' if enabled else 'disabled'
        log_audit_action(guild_id, f'Chatbot {status}', 'chatbot')
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to toggle chatbot'}), 500


# ============================================================================
# LEVELING API
# ============================================================================

@app.route('/api/guilds/<int:guild_id>/leveling', methods=['GET'])
@require_login
def get_leveling_settings_api(guild_id):
    """Get leveling settings."""
    settings = db.get_leveling_settings(guild_id)
    return jsonify(settings)


@app.route('/api/guilds/<int:guild_id>/leveling', methods=['POST'])
@require_login
def update_leveling_settings_api(guild_id):
    """Update leveling settings."""
    data = request.get_json()
    success = db.set_leveling_settings(guild_id, data)

    if success:
        log_audit_action(guild_id, 'Updated leveling settings', 'leveling')
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to update settings'}), 500


@app.route('/api/guilds/<int:guild_id>/leveling/roles', methods=['GET'])
@require_login
def get_level_roles_api(guild_id):
    """Get level role rewards."""
    # Check if user has access to this guild by validating token
    token = get_discord_token()
    if not token:
        return jsonify({'error': 'Forbidden'}), 403

    roles = db.get_level_roles(guild_id)
    # Convert role_id to string for consistency with Discord API
    for role in roles:
        role['role_id'] = str(role['role_id'])
    return jsonify(roles)


@app.route('/api/guilds/<int:guild_id>/leveling/roles', methods=['POST'])
@require_login
def add_level_role_api(guild_id):
    """Add a level role reward."""
    data = request.get_json()
    role_id = data.get('role_id')
    # Convert role_id to int if it's a string (for database query)
    if role_id and isinstance(role_id, str):
        role_id = int(role_id)
    success = db.add_level_role(
        guild_id,
        data.get('level'),
        role_id,
        data.get('stack', False)
    )

    if success:
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to add role'}), 500


@app.route('/api/guilds/<int:guild_id>/leveling/roles', methods=['PUT'])
@require_login
def update_level_role_api(guild_id):
    """Update a level role reward."""
    data = request.get_json()
    old_level = data.get('old_level')
    old_role_id = data.get('old_role_id')
    new_role_id = data.get('role_id')
    # Convert role_ids to int if they're strings (for database query)
    if old_role_id and isinstance(old_role_id, str):
        old_role_id = int(old_role_id)
    if new_role_id and isinstance(new_role_id, str):
        new_role_id = int(new_role_id)
    success = db.update_level_role(
        guild_id,
        old_level,
        old_role_id,
        data.get('level'),
        new_role_id,
        data.get('stack', False)
    )

    if success:
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to update role'}), 500


@app.route('/api/guilds/<int:guild_id>/leveling/roles', methods=['DELETE'])
@require_login
def remove_level_role_api(guild_id):
    """Remove a level role reward."""
    data = request.get_json()
    role_id = data.get('role_id')
    # Convert role_id to int if it's a string (for database query)
    if role_id and isinstance(role_id, str):
        role_id = int(role_id)
    success = db.remove_level_role(
        guild_id,
        data.get('level'),
        role_id
    )

    if success:
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to remove role'}), 500


# ============================================================================
# EXCLUDED ROLES API (Roles that cannot gain XP)
# ============================================================================

@app.route('/api/guilds/<int:guild_id>/leveling/excluded-roles', methods=['GET'])
@require_login
def get_excluded_roles_api(guild_id):
    """Get all excluded roles for a guild."""
    excluded_roles = db.get_excluded_roles(guild_id)
    # Convert role IDs to strings to avoid JavaScript precision loss with large IDs
    excluded_roles_str = [str(role_id) for role_id in excluded_roles]
    return jsonify({'data': excluded_roles_str})


@app.route('/api/guilds/<int:guild_id>/leveling/excluded-roles', methods=['POST'])
@require_login
def add_excluded_role_api(guild_id):
    """Add a role to the excluded roles list."""
    data = request.get_json()
    role_id = data.get('role_id')
    if role_id and isinstance(role_id, str):
        role_id = int(role_id)

    if not role_id:
        return jsonify({'error': 'Role ID is required'}), 400

    success = db.add_excluded_role(guild_id, role_id)
    if success:
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to add excluded role'}), 500


@app.route('/api/guilds/<int:guild_id>/leveling/excluded-roles', methods=['DELETE'])
@require_login
def remove_excluded_role_api(guild_id):
    """Remove a role from the excluded roles list."""
    data = request.get_json()
    role_id = data.get('role_id')
    if role_id and isinstance(role_id, str):
        role_id = int(role_id)

    if not role_id:
        return jsonify({'error': 'Role ID is required'}), 400

    success = db.remove_excluded_role(guild_id, role_id)
    if success:
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to remove excluded role'}), 500


@app.route('/api/guilds/<int:guild_id>/leaderboard', methods=['GET'])
@require_login
def get_leaderboard_api(guild_id):
    """Get guild leaderboard - shows all guild members with XP data."""
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)

    headers = {'Authorization': f'Bot {BOT_TOKEN}'}

    # Get excluded roles for this guild
    excluded_role_ids = set(db.get_excluded_roles(guild_id))

    # Fetch all guild members from Discord
    all_members = []
    after = None

    while True:
        params = {'limit': 1000}
        if after:
            params['after'] = after

        try:
            response = requests.get(f'{DISCORD_API_BASE}/guilds/{guild_id}/members', headers=headers, params=params)
            if response.status_code == 200:
                members = response.json()
                if not members:
                    break
                all_members.extend(members)
                after = members[-1]['user']['id']
                # Break if we got less than limit (last page)
                if len(members) < 1000:
                    break
            else:
                print(f'[ERROR] Failed to fetch guild members: {response.status_code}')
                break
        except Exception as e:
            print(f'[ERROR] Exception fetching guild members: {e}')
            break

    # Get existing XP data from database
    xp_data = db.get_all_guild_users_xp(guild_id)

    # Create a map of user_id -> XP data for quick lookup
    xp_map = {str(row['user_id']): row for row in xp_data}

    # Merge member data with XP data, excluding users with excluded roles
    leaderboard = []
    for member in all_members:
        user = member['user']
        user_id = str(user['id'])
        user_roles = member.get('roles', [])

        # Skip users with excluded roles
        if excluded_role_ids and any(int(role_id) in excluded_role_ids for role_id in user_roles):
            continue

        # Get XP data or use defaults
        user_xp = xp_map.get(user_id, {
            'xp': 0,
            'level': 1,
            'total_xp': 0,
            'message_count': 0
        })

        entry = {
            'user_id': user_id,
            'xp': user_xp.get('xp', 0),
            'level': user_xp.get('level', 1),
            'total_xp': user_xp.get('total_xp', 0),
            'message_count': user_xp.get('message_count', 0),
            'display_name': member.get('nick') or user.get('global_name') or user.get('username', f'User {user_id}'),
            'username': user.get('username', f'user_{user_id}'),
            'avatar_url': get_avatar_url_from_user_data(user, user_id)
        }
        leaderboard.append(entry)

    # Sort by level (desc), then by XP (desc), then by total_xp (desc)
    leaderboard.sort(key=lambda x: (x['level'], x['xp'], x['total_xp']), reverse=True)

    # Apply pagination after sorting
    total_count = len(leaderboard)
    leaderboard = leaderboard[offset:offset + limit]

    # Add rank info
    for i, entry in enumerate(leaderboard):
        entry['rank'] = offset + i + 1

    return jsonify({
        'data': leaderboard,
        'total': total_count,
        'offset': offset,
        'limit': limit
    })


def get_avatar_url_from_user_data(user_data, user_id):
    """Get user avatar URL from user data."""
    avatar_hash = user_data.get('avatar')
    if not avatar_hash:
        discriminator = user_data.get('discriminator', '0')
        return get_default_avatar(discriminator, user_id)
    # Return URL WITHOUT extension - Discord CDN auto-detects format (PNG/GIF)
    # This handles GIF avatars for Nitro users
    return f'https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}'


def get_avatar_url(user_info, user_id):
    """Get user avatar URL."""
    avatar_hash = user_info.get('avatar')
    if not avatar_hash:
        return None
    # Return URL WITHOUT extension - Discord CDN auto-detects format (PNG/GIF)
    return f'https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}'


def get_default_avatar(discriminator, user_id):
    """Get default avatar URL based on discriminator or user ID."""
    # New username system uses 0 discriminator
    disc = int(discriminator) if discriminator != '0' else int(user_id) % 5
    return f'https://cdn.discordapp.com/embed/avatars/{disc}.png'


# ============================================================================
# USER MANAGEMENT API
# ============================================================================

@app.route('/api/guilds/<int:guild_id>/users/<int:user_id>/reset', methods=['POST'])
@require_login
def reset_user_xp_api(guild_id, user_id):
    """Reset a user's XP to level 1."""
    success = db.reset_user_xp(guild_id, user_id)
    if success:
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to reset user XP'}), 500


@app.route('/api/guilds/<int:guild_id>/users/<int:user_id>/set', methods=['POST'])
@require_login
def set_user_xp_api(guild_id, user_id):
    """Set a user's level and XP directly."""
    data = request.get_json()
    level = data.get('level')
    xp = data.get('xp')

    if level is None or xp is None or not isinstance(level, (int, float)) or not isinstance(xp, (int, float)):
        return jsonify({'error': 'Level and XP are required'}), 400

    success = db.set_user_xp(guild_id, user_id, int(level), int(xp))
    if success:
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to set user XP'}), 500



@app.route('/api/guilds/<int:guild_id>/leveling/toggle', methods=['POST'])
@require_login
def toggle_leveling_api(guild_id):
    """Toggle leveling enabled status."""
    data = request.get_json()
    enabled = data.get('enabled', False)
    success = db.toggle_leveling(guild_id, enabled)

    if success:
        status = 'enabled' if enabled else 'disabled'
        log_audit_action(guild_id, f'Leveling {status}', 'leveling')
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to toggle leveling'}), 500


# ============================================================================
# MODERATION API
# ============================================================================

@app.route('/api/guilds/<int:guild_id>/moderation/roles', methods=['GET'])
@require_login
def get_moderation_roles_api(guild_id):
    """Get moderation roles."""
    roles = db.get_moderation_roles(guild_id)
    return jsonify(roles)


@app.route('/api/guilds/<int:guild_id>/moderation/roles', methods=['POST'])
@require_login
def add_moderation_role_api(guild_id):
    """Add a moderation role."""
    data = request.get_json()
    role_id = data.get('role_id')
    success = db.add_moderation_role(guild_id, role_id)

    if success:
        log_audit_action(guild_id, f'Added moderation role: {role_id}', 'moderation')
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to add role'}), 500


@app.route('/api/guilds/<int:guild_id>/moderation/roles', methods=['DELETE'])
@require_login
def remove_moderation_role_api(guild_id):
    """Remove a moderation role."""
    data = request.get_json()
    role_id = data.get('role_id')
    success = db.remove_moderation_role(guild_id, role_id)

    if success:
        log_audit_action(guild_id, f'Removed moderation role: {role_id}', 'moderation')
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to remove role'}), 500


@app.route('/api/guilds/<int:guild_id>/moderation/logs', methods=['GET'])
@require_login
def get_moderation_logs_api(guild_id):
    """Get moderation logs."""
    limit = request.args.get('limit', 50, type=int)
    logs = db.get_moderation_logs(guild_id, limit)
    return jsonify(logs)


# ============================================================================
# AUDIT LOGS API
# ============================================================================

@app.route('/api/guilds/<int:guild_id>/audit-logs', methods=['GET'])
@require_login
def get_audit_logs_api(guild_id):
    """Get audit logs for a guild."""
    limit = request.args.get('limit', 100, type=int)
    logs = db.get_audit_logs(guild_id, limit)
    return jsonify(logs)


# ============================================================================
# MEMBERS API
# ============================================================================

@app.route('/api/guilds/<int:guild_id>/members', methods=['GET'])
@require_login
def get_members_api(guild_id):
    """Get guild members with pagination and search."""
    limit = min(request.args.get('limit', 50, type=int), 100)
    offset = request.args.get('offset', 0, type=int)
    search = request.args.get('search', '').strip().lower()

    headers = {'Authorization': f'Bot {BOT_TOKEN}'}

    # Fetch all guild members from Discord
    all_members = []
    after = None

    while True:
        params = {'limit': 1000}
        if after:
            params['after'] = after

        try:
            response = requests.get(f'{DISCORD_API_BASE}/guilds/{guild_id}/members', headers=headers, params=params)
            if response.status_code == 200:
                members = response.json()
                if not members:
                    break
                all_members.extend(members)
                after = members[-1]['user']['id']
                if len(members) < 1000:
                    break
            else:
                print(f'[ERROR] Failed to fetch guild members: {response.status_code}')
                break
        except Exception as e:
            print(f'[ERROR] Exception fetching guild members: {e}')
            break

    # Filter by search if provided
    if search:
        filtered_members = []
        for member in all_members:
            user = member['user']
            username = user.get('username', '').lower()
            display_name = (member.get('nick') or user.get('global_name') or '').lower()
            if search in username or search in display_name:
                filtered_members.append(member)
        all_members = filtered_members

    # Get roles for this guild from Discord
    roles = []
    try:
        response = requests.get(f'{DISCORD_API_BASE}/guilds/{guild_id}/roles', headers=headers)
        if response.status_code == 200:
            roles = response.json()
    except Exception as e:
        print(f'[ERROR] Failed to get guild roles: {e}')

    roles_map = {str(r['id']): r for r in roles}

    # Format member data
    formatted_members = []
    for member in all_members:
        user = member['user']
        user_id = str(user['id'])

        entry = {
            'user_id': user_id,
            'username': user.get('username', f'user_{user_id}'),
            'global_name': user.get('global_name'),
            'display_name': member.get('nick') or user.get('global_name') or user.get('username'),
            'avatar': get_avatar_url_from_user_data(user, user_id),
            'roles': [str(r) for r in member.get('roles', [])],
            'joined_at': member.get('joined_at'),
            'premium_since': member.get('premium_since'),
            'communication_disabled_until': member.get('communication_disabled_until')
        }

        # Add role names and colors
        role_info = []
        member_roles = member.get('roles', [])
        for role_id in member_roles:
            role_data = roles_map.get(str(role_id))
            if role_data:
                role_info.append({
                    'id': str(role_data['id']),
                    'name': role_data['name'],
                    'color': role_data.get('color', 0),
                    'position': role_data.get('position', 0)
                })

        # Sort by position (highest first)
        role_info.sort(key=lambda r: r['position'], reverse=True)
        entry['role_info'] = role_info

        # Get highest role color (non-zero)
        entry['color'] = next((r['color'] for r in role_info if r['color'] > 0), 0)

        formatted_members.append(entry)

    # Sort by display name
    formatted_members.sort(key=lambda x: x['display_name'].lower())

    # Pagination
    total = len(formatted_members)
    paginated_members = formatted_members[offset:offset + limit]

    return jsonify({
        'members': paginated_members,
        'total': total,
        'limit': limit,
        'offset': offset
    })


@app.route('/api/guilds/<int:guild_id>/members/<string:user_id>/ban', methods=['POST'])
@require_login
def ban_member_api(guild_id, user_id):
    """Ban a member from the guild."""
    data = request.get_json()
    reason = data.get('reason', '')
    delete_message_days = data.get('delete_message_days', 0)

    headers = {'Authorization': f'Bot {BOT_TOKEN}'}
    payload = {
        'reason': reason,
        'delete_message_days': min(delete_message_days, 7)
    }

    try:
        response = requests.put(
            f'{DISCORD_API_BASE}/guilds/{guild_id}/bans/{user_id}',
            headers=headers,
            json=payload
        )

        if response.status_code == 200:
            log_audit_action(guild_id, f'Banned user: {user_id}', 'moderation', reason)
            return jsonify({'success': True})
        else:
            return jsonify({'error': f'Failed to ban user: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/guilds/<int:guild_id>/members/<string:user_id>/kick', methods=['POST'])
@require_login
def kick_member_api(guild_id, user_id):
    """Kick a member from the guild."""
    data = request.get_json()
    reason = data.get('reason', '')

    headers = {'Authorization': f'Bot {BOT_TOKEN}'}
    payload = {'reason': reason} if reason else {}

    try:
        response = requests.delete(
            f'{DISCORD_API_BASE}/guilds/{guild_id}/members/{user_id}',
            headers=headers,
            json=payload
        )

        if response.status_code == 204:
            log_audit_action(guild_id, f'Kicked user: {user_id}', 'moderation', reason)
            return jsonify({'success': True})
        else:
            return jsonify({'error': f'Failed to kick user: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/guilds/<int:guild_id>/members/<string:user_id>/timeout', methods=['POST'])
@require_login
def timeout_member_api(guild_id, user_id):
    """Timeout a member."""
    data = request.get_json()
    duration_minutes = data.get('duration_minutes', 60)
    reason = data.get('reason', '')

    # Calculate expiration timestamp (in seconds from now)
    duration_seconds = duration_minutes * 60
    expires_at = int((datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)).timestamp())

    headers = {'Authorization': f'Bot {BOT_TOKEN}'}
    payload = {
        'communication_disabled_until': expires_at.isoformat() + 'Z',
        'reason': reason
    }

    try:
        response = requests.patch(
            f'{DISCORD_API_BASE}/guilds/{guild_id}/members/{user_id}',
            headers=headers,
            json=payload
        )

        if response.status_code == 200:
            log_audit_action(guild_id, f'Timeouted user: {user_id} for {duration_minutes} minutes', 'moderation', reason)
            return jsonify({'success': True})
        else:
            return jsonify({'error': f'Failed to timeout user: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/guilds/<int:guild_id>/members/<string:user_id>/timeout', methods=['DELETE'])
@require_login
def remove_timeout_member_api(guild_id, user_id):
    """Remove timeout from a member."""
    headers = {'Authorization': f'Bot {BOT_TOKEN}'}
    payload = {'communication_disabled_until': None}

    try:
        response = requests.patch(
            f'{DISCORD_API_BASE}/guilds/{guild_id}/members/{user_id}',
            headers=headers,
            json=payload
        )

        if response.status_code == 200:
            log_audit_action(guild_id, f'Removed timeout from user: {user_id}', 'moderation')
            return jsonify({'success': True})
        else:
            return jsonify({'error': f'Failed to remove timeout: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# WELCOME API
# ============================================================================

@app.route('/api/guilds/<int:guild_id>/welcome/roles', methods=['GET'])
@require_login
def get_welcome_roles_api(guild_id):
    """Get welcome roles."""
    roles = db.get_welcome_roles(guild_id)
    return jsonify(roles)


@app.route('/api/guilds/<int:guild_id>/welcome/roles', methods=['POST'])
@require_login
def add_welcome_role_api(guild_id):
    """Add a welcome role."""
    data = request.get_json()
    success = db.add_welcome_role(guild_id, data.get('role_id'))

    if success:
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to add role'}), 500


@app.route('/api/guilds/<int:guild_id>/welcome/roles', methods=['DELETE'])
@require_login
def remove_welcome_role_api(guild_id):
    """Remove a welcome role."""
    data = request.get_json()
    success = db.remove_welcome_role(guild_id, data.get('role_id'))

    if success:
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to remove role'}), 500


@app.route('/api/guilds/<int:guild_id>/channels', methods=['GET'])
@require_login
def get_guild_channels_api(guild_id):
    """Get text channels for a guild."""
    try:
        headers = {'Authorization': f'Bot {BOT_TOKEN}'}
        response = requests.get(f'{DISCORD_API_BASE}/guilds/{guild_id}/channels', headers=headers)

        if response.status_code != 200:
            return jsonify({'error': 'Failed to fetch channels'}), 500

        all_channels = response.json()

        # Filter only text channels (type 0 is text channel)
        text_channels = [
            {
                'id': ch['id'],
                'name': ch['name'],
                'type': ch['type'],
                'position': ch.get('position', 0),
                'parent_id': ch.get('parent_id')
            }
            for ch in all_channels
            if ch.get('type') == 0  # 0 = text channel
        ]

        # Sort by position
        text_channels.sort(key=lambda x: x['position'])

        return jsonify(text_channels)

    except Exception as e:
        print(f'[ERROR] Failed to get guild channels: {e}')
        return jsonify({'error': 'Failed to fetch channels'}), 500


@app.route('/api/guilds/<int:guild_id>/roles', methods=['GET'])
@require_login
def get_guild_roles_api(guild_id):
    """Get all roles for a guild."""
    try:
        headers = {'Authorization': f'Bot {BOT_TOKEN}'}
        response = requests.get(f'{DISCORD_API_BASE}/guilds/{guild_id}/roles', headers=headers)

        if response.status_code != 200:
            return jsonify({'error': 'Failed to fetch roles'}), 500

        all_roles = response.json()

        # Filter out @everyone role and sort by position
        roles = [
            {
                'id': r['id'],
                'name': r['name'],
                'color': r['color'],
                'position': r.get('position', 0),
                'permissions': r.get('permissions', 0)
            }
            for r in all_roles
            if r['name'] != '@everyone'  # Skip @everyone
        ]

        # Sort by position (higher position = lower number, so reverse sort)
        roles.sort(key=lambda x: x['position'], reverse=True)

        return jsonify(roles)

    except Exception as e:
        print(f'[ERROR] Failed to get guild roles: {e}')
        return jsonify({'error': 'Failed to fetch roles'}), 500


# ============================================================================
# USER MUSIC GENRES API
# ============================================================================

@app.route('/api/music/genres', methods=['GET'])
@require_login
def get_user_music_genres():
    """Get current user's custom music genres."""
    user = get_discord_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user_id = int(user.get('id', 0))
    genres = db.get_user_genres(user_id)

    # Convert id to string for JavaScript compatibility
    for genre in genres:
        genre['id'] = str(genre['id'])
        genre['user_id'] = str(genre['user_id'])

    return jsonify(genres)


@app.route('/api/music/genres', methods=['POST'])
@require_login
def add_user_music_genre():
    """Add a custom music genre for the current user."""
    user = get_discord_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    genre_name = data.get('genre_name', '').strip()
    search_query = data.get('search_query', '').strip()
    emoji = data.get('emoji', '🎵').strip() or '🎵'

    if not genre_name:
        return jsonify({'error': 'Genre name is required'}), 400
    if not search_query:
        return jsonify({'error': 'Search query is required'}), 400

    user_id = int(user.get('id', 0))
    success = db.add_user_genre(user_id, genre_name, search_query, emoji)

    if success:
        return jsonify({'success': True, 'message': 'Genre added successfully'})
    return jsonify({'error': 'Failed to add genre'}), 500


@app.route('/api/music/genres/<int:genre_id>', methods=['DELETE'])
@require_login
def delete_user_music_genre(genre_id):
    """Delete a custom music genre for the current user."""
    user = get_discord_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user_id = int(user.get('id', 0))
    success = db.delete_user_genre(user_id, genre_id)

    if success:
        return jsonify({'success': True, 'message': 'Genre deleted successfully'})
    return jsonify({'error': 'Genre not found or failed to delete'}), 404


# ============================================================================
# FILE UPLOAD API
# ============================================================================

# Configure upload folder and allowed extensions
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'banners'), exist_ok=True)


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/upload/banner', methods=['POST'])
@require_login
def upload_banner():
    """Upload a banner image for welcome/goodbye messages."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed: png, jpg, jpeg, gif, webp'}), 400

        # Check file size using content_length
        file_size = file.content_length
        if file_size and file_size > MAX_FILE_SIZE:
            return jsonify({'error': f'File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB'}), 400

        # Generate unique filename
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{int(time.time())}{ext}"

        # Save file (stream to disk without seek operations)
        filepath = os.path.join(UPLOAD_FOLDER, 'banners', unique_filename)
        file.save(filepath)

        # Return the full URL (not filesystem path)
        url_path = f"/uploads/banners/{unique_filename}"
        full_url = f"{DASHBOARD_BASE_URL}{url_path}"

        print(f"[UPLOAD] Saved banner: {filepath}")
        print(f"[UPLOAD] Returning URL: {full_url}")

        return jsonify({
            'success': True,
            'url': full_url,
            'filename': unique_filename
        })
    except Exception as e:
        print(f"[ERROR] Upload failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500


@app.route('/uploads/banners/<filename>')
def serve_banner(filename):
    """Serve uploaded banner files."""
    try:
        from flask import send_from_directory
        return send_from_directory(os.path.join(UPLOAD_FOLDER, 'banners'), filename)
    except Exception as e:
        print(f"[ERROR] Failed to serve banner: {e}")
        return jsonify({'error': 'File not found'}), 404


@app.route('/api/proxy/avatar')
def proxy_avatar():
    """Proxy Discord avatar URLs to avoid CORS issues."""
    avatar_url = request.args.get('url')
    if not avatar_url:
        return jsonify({'error': 'URL required'}), 400

    try:
        response = requests.get(avatar_url, timeout=10)
        if response.status_code == 200:
            # Proxy the image with proper CORS headers
            from flask import Response
            proxied_response = Response(response.content, mimetype=response.headers.get('Content-Type', 'image/png'))
            proxied_response.headers['Cache-Control'] = 'public, max-age=86400'  # Cache for 1 day
            proxied_response.headers['Access-Control-Allow-Origin'] = '*'
            return proxied_response
        return jsonify({'error': 'Failed to fetch avatar'}), 404
    except Exception as e:
        print(f"[ERROR] Failed to proxy avatar: {e}")
        return jsonify({'error': 'Failed to fetch avatar'}), 500


# ============================================================================
# FRONTEND SERVE (SPA) - Must be LAST route
# ============================================================================

@app.route('/<path:path>')
def serve_frontend(path=''):
    """Serve Vue frontend from dist folder for SPA routing."""
    # First check if it's a static file in dist
    if path and os.path.exists(os.path.join(FRONTEND_DIST, path)):
        return send_from_directory(FRONTEND_DIST, path)
    # For SPA routing, always return index.html
    return send_from_directory(FRONTEND_DIST, 'index.html')


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors - serve Vue frontend for SPA routing."""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not found'}), 404
    # For non-API routes, serve index.html for SPA routing
    return send_from_directory(FRONTEND_DIST, 'index.html')


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    if request.path.startswith('/api/'):
        response = jsonify({'error': 'Internal server error', 'details': str(error)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 500
    # Serve index.html for SPA
    return send_from_directory(FRONTEND_DIST, 'index.html')


# ============================================================================
# DEVELOPMENT/PRODUCTION
# ============================================================================

if __name__ == '__main__':
    # Initialize database
    db.init_db()

    # Run development server
    # Use PORT environment variable for cloud deployment, default to 5001 for local
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
