"""
Leveling Cog
============
Sistem leveling dan XP untuk Discord bot.
"""

import discord
from discord.ext import commands
from datetime import datetime
import asyncio
import config

try:
    from dashboard.backend import database as db
    HAS_DATABASE = True
except ImportError:
    HAS_DATABASE = False


# ==================== UTILITY FUNCTIONS ====================

def xp_required_for_level(level: int, base_xp: int = None, xp_increment: int = None) -> int:
    """
    Hitung XP yang dibutuhkan untuk mencapai level tertentu dari level 0.
    XP reset ke 0 setelah setiap level up.

    Level 1 -> 2: 150 XP
    Level 2 -> 3: 200 XP (150 + 50)
    Level 3 -> 4: 250 XP (150 + 50*2)
    Level n -> n+1: 150 + (n-1)*50
    """
    base_xp = base_xp or getattr(config, 'BASE_XP_PER_LEVEL', 150)
    xp_increment = xp_increment or getattr(config, 'XP_INCREMENT_PER_LEVEL', 50)

    if level <= 1:
        return base_xp
    return base_xp + (level - 1) * xp_increment


# ==================== PERMISSION CHECK ====================

def has_leveling_role():
    """Custom check untuk leveling admin permission."""
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.author.id == ctx.guild.owner_id:
            return True

        if HAS_DATABASE:
            roles = db.get_moderation_roles(ctx.guild.id)
            if roles:
                user_roles = [r.id for r in ctx.author.roles]
                if any(r in user_roles for r in roles):
                    return True

        # Fallback ke Discord permissions
        return ctx.author.guild_permissions.manage_guild
    return commands.check(predicate)


# ==================== LEVELING COG ====================

class Leveling(commands.Cog):
    """Cog untuk leveling dan XP system."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Cooldown tracking: {(guild_id, user_id): datetime}
        self.xp_cooldowns = {}

        # Initialize database on load
        if HAS_DATABASE:
            db.init_db()
            print("[Leveling] Database initialized")

    def _create_embed(self, title: str, description: str, color: int) -> discord.Embed:
        """Helper untuk membuat embed."""
        return discord.Embed(
            title=title,
            description=description,
            color=color
        )

    def _get_leveling_settings(self, guild_id: int) -> dict:
        """Dapatkan guild leveling settings."""
        if HAS_DATABASE:
            settings = db.get_leveling_settings(guild_id)
            if settings:
                # Parse exempt_roles from JSON if it's a string
                exempt_roles = settings.get('exempt_roles', [])
                if isinstance(exempt_roles, str):
                    import json
                    try:
                        exempt_roles = json.loads(exempt_roles)
                    except:
                        exempt_roles = []

                return {
                    'leveling_enabled': settings.get('leveling_enabled', 1),
                    'xp_per_message': settings.get('xp_per_message', 10),
                    'cooldown_seconds': settings.get('cooldown_seconds', 60),
                    'min_message_length': settings.get('min_message_length', 0),
                    'level_up_channel_id': settings.get('level_up_channel_id'),
                    'notify_level_up': settings.get('notify_level_up', 1),
                    'level_up_image_url': settings.get('level_up_image_url'),
                    'level_up_message': settings.get('level_up_message'),
                    'exempt_roles': exempt_roles
                }
        return {
            'leveling_enabled': getattr(config, 'LEVELING_ENABLED_BY_DEFAULT', True),
            'xp_per_message': getattr(config, 'DEFAULT_XP_PER_MESSAGE', 10),
            'cooldown_seconds': getattr(config, 'DEFAULT_XP_COOLDOWN', 60),
            'min_message_length': 0,
            'level_up_channel_id': None,
            'notify_level_up': True,
            'level_up_image_url': None,
            'level_up_message': None,
            'exempt_roles': []
        }

    def _get_user_xp(self, guild_id: int, user_id: int) -> dict:
        """Dapatkan user XP data."""
        if HAS_DATABASE:
            data = db.get_user_xp(guild_id, user_id)
            if data:
                result = {
                    'total_xp': data.get('total_xp', 0),
                    'current_level': data.get('level', 0),
                    'current_xp': data.get('xp', 0),
                    'message_count': data.get('message_count', 0),
                    'last_level_up': data.get('last_xp_gain', 0)
                }
                print(f"[Leveling] DEBUG: get_user_xp({guild_id}, {user_id}) = {result}")
                return result
            else:
                print(f"[Leveling] DEBUG: get_user_xp({guild_id}, {user_id}) = NOT FOUND")
        return {'total_xp': 0, 'current_level': 0, 'current_xp': 0, 'message_count': 0, 'last_level_up': 0}

    async def _handle_level_up(self, user: discord.Member, guild_id: int, old_level: int, new_level: int, current_xp: int):
        """Handle level up: notification and roles. Database already handled level calculation."""
        settings = self._get_leveling_settings(guild_id)

        print(f"[Leveling] _handle_level_up: user={user.display_name}, level {old_level} -> {new_level}, xp={current_xp}")

        # Tentukan channel untuk notifikasi
        channel = None
        if settings.get('level_up_channel_id'):
            channel = user.guild.get_channel(settings['level_up_channel_id'])

        # Kirim notifikasi
        if settings.get('notify_level_up'):
            target_channel = channel or user.guild.system_channel
            if target_channel:
                try:
                    # Get custom message template or use default
                    custom_message = settings.get('level_up_message')
                    if custom_message:
                        # Replace placeholders
                        message = custom_message.replace('{user_mention}', user.mention)
                        message = message.replace('{level}', str(new_level))
                        message = message.replace('{username}', user.display_name)
                        message = message.replace('\\n', '\n')  # Convert \n to actual newlines
                    else:
                        # Default message
                        message = f"🎉 **Selamat {user.mention}!**\nKamu telah mencapai **Level {new_level}**!"

                    # Check if custom image URL is set
                    custom_image_url = settings.get('level_up_image_url')

                    if custom_image_url:
                        # Send image with text message (no embed - shows full size image)
                        await target_channel.send(content=message)
                        await target_channel.send(content=custom_image_url)
                    else:
                        # Use default embed format
                        embed = discord.Embed(
                            title="🎉 Level Up!",
                            description=f"Selamat {user.mention}!\nKamu telah mencapai **Level {new_level}**!",
                            color=config.COLORS.get("leveling", 0xFFD700),
                            timestamp=datetime.utcnow()
                        )
                        embed.set_thumbnail(url=user.display_avatar.url)
                        embed.set_footer(text="Terus chat untuk mendapatkan lebih banyak XP!")
                        await target_channel.send(content=user.mention, embed=embed)
                except Exception as e:
                    print(f"[Leveling] Error sending level up notification: {e}")

        # Award roles
        await self._award_level_roles(user, guild_id, new_level)

        # Update last_level_up timestamp in database
        if HAS_DATABASE:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE user_xp SET last_level_up = ? WHERE guild_id = ? AND user_id = ?
            """, (new_level, guild_id, user.id))
            conn.commit()
            conn.close()

    async def _award_level_roles(self, user: discord.Member, guild_id: int, level: int):
        """Award roles untuk mencapai level tertentu."""
        if not HAS_DATABASE:
            print(f"[Leveling] _award_level_roles: HAS_DATABASE is False, skipping")
            return

        print(f"[Leveling] _award_level_roles called: user={user.display_name}, guild_id={guild_id}, level={level}")

        role_ids = db.get_all_level_roles_below(guild_id, level)
        print(f"[Leveling] get_all_level_roles_below returned: {role_ids}")

        if not role_ids:
            print(f"[Leveling] No level roles found for guild {guild_id} below level {level}")
            return

        user_role_ids = [r.id for r in user.roles]
        print(f"[Leveling] User's current roles: {user_role_ids}")

        for role_id in role_ids:
            role = user.guild.get_role(role_id)
            print(f"[Leveling] Checking role_id {role_id}: role={role.name if role else 'None'}")
            if role and role.id not in user_role_ids:
                try:
                    # Check bot can assign this role
                    if role < user.guild.me.top_role:
                        await user.add_roles(role, reason=f"Level {level} reward")
                        print(f"[Leveling] Awarded role {role.name} (ID: {role.id}) to {user.display_name} for reaching level {level}")
                    else:
                        print(f"[Leveling] Cannot award role {role.name} - bot's top_role is lower than the role")
                except discord.Forbidden:
                    print(f"[Leveling] No permission to add role {role.name}")
                except Exception as e:
                    print(f"[Leveling] Error adding role: {e}")
            elif not role:
                print(f"[Leveling] Role {role_id} not found in guild")
            else:
                print(f"[Leveling] User already has role {role.name}")

    # ==================== EVENT LISTENERS ====================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Award XP untuk pesan."""
        # Skip jika bot message atau DM
        if message.author.bot or not message.guild:
            return

        guild_id = message.guild.id
        user_id = message.author.id

        settings = self._get_leveling_settings(guild_id)
        if not settings.get('leveling_enabled'):
            return

        # Cek exempt roles
        exempt_roles = settings.get('exempt_roles', [])
        if exempt_roles:
            user_role_ids = [role.id for role in message.author.roles]
            if any(role_id in user_role_ids for role_id in exempt_roles):
                return  # User has exempt role, skip XP

        # Cek excluded roles dari database (separate feature)
        if HAS_DATABASE:
            if db.is_user_excluded(guild_id, [role.id for role in message.author.roles]):
                return  # User has excluded role, skip XP

        # Cek minimum panjang pesan
        min_length = settings.get('min_message_length', 0)
        if min_length > 0 and len(message.content.strip()) < min_length:
            return  # Pesan terlalu pendek, skip XP

        # Cek cooldown
        cooldown_key = (guild_id, user_id)
        last_time = self.xp_cooldowns.get(cooldown_key)
        now = datetime.utcnow()

        cooldown_seconds = settings.get('cooldown_seconds', 60)

        if last_time and (now - last_time).total_seconds() < cooldown_seconds:
            return  # Masih cooldown

        # Update cooldown
        self.xp_cooldowns[cooldown_key] = now

        # Dapatkan data saat ini
        current_data = self._get_user_xp(guild_id, user_id)
        old_level = current_data.get('current_level', 0)

        # Award XP
        xp_amount = settings.get('xp_per_message', 10)

        # Simpan ke database dan dapatkan nilai baru
        if HAS_DATABASE:
            try:
                leveled_up, new_level, new_xp = db.add_user_xp(guild_id, user_id, xp_amount)
                print(f"[Leveling] Added {xp_amount} XP to user {user_id} in guild {guild_id} (Level: {old_level} -> {new_level}, XP: {new_xp}, leveled_up={leveled_up})")

                # Handle level up if database detected one
                if leveled_up:
                    print(f"[Leveling] Level up detected! Calling _handle_level_up from level {old_level} to {new_level}")
                    await self._handle_level_up(message.author, guild_id, old_level, new_level, new_xp)
            except Exception as e:
                print(f"[Leveling] ERROR: Failed to add XP for user {user_id} in guild {guild_id}: {e}")

            db.update_message_count(guild_id, user_id)

    # ==================== LEVEL COMMAND ====================

    @commands.command(name="level", aliases=["rank", "xp"])
    async def level(self, ctx: commands.Context, member: discord.Member = None):
        """Tampilkan level dan XP kamu atau member lain."""
        member = member or ctx.author
        guild_id = ctx.guild.id
        user_id = member.id

        data = self._get_user_xp(guild_id, user_id)
        current_level = data.get('current_level', 0)
        current_xp = data.get('current_xp', 0)
        total_xp = data.get('total_xp', 0)
        message_count = data.get('message_count', 0)

        # Hitung XP yang dibutuhkan untuk next level
        xp_required = xp_required_for_level(current_level + 1)

        # Dapatkan rank
        rank = 0
        if HAS_DATABASE:
            rank = db.get_user_rank(guild_id, user_id)

        # Buat progress bar
        progress_percent = (current_xp / xp_required) if xp_required > 0 else 1
        bar_length = 10
        filled = int(progress_percent * bar_length)
        progress_bar = "▓" * filled + "░" * (bar_length - filled)

        embed = discord.Embed(
            title=f"📊 Level Card - {member.display_name}",
            color=config.COLORS.get("leveling", 0xFFD700)
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(name="Level", value=f"**{current_level}**", inline=True)
        embed.add_field(name="Total XP", value=f"**{total_xp:,}**", inline=True)
        embed.add_field(name="Rank", value=f"**#{rank}**" if rank > 0 else "**N/A**", inline=True)
        embed.add_field(name="Messages", value=f"**{message_count:,}**", inline=True)

        embed.add_field(
            name=f"Progress to Level {current_level + 1}",
            value=f"{progress_bar} `{current_xp:,}`/`{xp_required:,}` XP ({progress_percent*100:.1f}%)",
            inline=False
        )

        await ctx.send(embed=embed)

    # ==================== LEADERBOARD COMMAND ====================

    @commands.command(name="leaderboard", aliases=["lb", "top"])
    async def leaderboard(self, ctx: commands.Context, page: int = 1):
        """Tampilkan server XP leaderboard."""
        per_page = 10
        offset = (page - 1) * per_page

        if not HAS_DATABASE:
            embed = self._create_embed(
                "❌ Error",
                "Leaderboard tidak tersedia.",
                config.COLORS["error"]
            )
            return await ctx.send(embed=embed)

        # Fetch lebih banyak data sebagai buffer untuk user yang leave (2x per_page)
        fetch_limit = per_page * 2
        leaderboard_data = db.get_guild_leaderboard(ctx.guild.id, limit=fetch_limit, offset=offset)

        if not leaderboard_data:
            embed = self._create_embed(
                "📊 Leaderboard",
                "Belum ada data. Kirim pesan untuk mendapatkan XP!",
                config.COLORS["info"]
            )
            return await ctx.send(embed=embed)

        description = ""
        display_count = 0  # Jumlah user yang valid ditampilkan
        data_index = 0  # Index untuk leaderboard_data

        while display_count < per_page and data_index < len(leaderboard_data):
            entry = leaderboard_data[data_index]
            data_index += 1

            entry_user_id = entry['user_id']
            entry_level = entry.get('level', 0)
            entry_xp = entry.get('xp', 0)

            # Hitung rank sebenarnya (offset + data_index)
            actual_rank = offset + data_index

            # Coba dapatkan member dari cache dulu (lebih cepat)
            member = ctx.guild.get_member(entry_user_id)
            if member:
                name = member.display_name
            else:
                # Jika tidak ada di cache, coba fetch dari Discord API
                try:
                    member = await ctx.guild.fetch_member(entry_user_id)
                    name = member.display_name
                except (discord.NotFound, discord.HTTPException):
                    # User sudah leave server, skip entry ini
                    continue

            # Medal berdasarkan actual_rank
            medal = ""
            if actual_rank == 1: medal = "🥇"
            elif actual_rank == 2: medal = "🥈"
            elif actual_rank == 3: medal = "🥉"

            xp_needed = xp_required_for_level(entry_level + 1)
            description += f"**{actual_rank}.** {medal} {name} - Level **{entry_level}** ({entry_xp:,}/{xp_needed:,} XP)\n"
            display_count += 1

        if not description:
            embed = self._create_embed(
                "📊 Leaderboard",
                f"Halaman {page} kosong atau semua member sudah leave server.",
                config.COLORS["info"]
            )
            return await ctx.send(embed=embed)

        embed = discord.Embed(
            title=f"🏆 XP Leaderboard - {ctx.guild.name}",
            description=description,
            color=config.COLORS.get("leveling", 0xFFD700)
        )
        embed.set_footer(text=f"Halaman {page} • Gunakan !leaderboard {page + 1} untuk lebih banyak")

        await ctx.send(embed=embed)

    # ==================== SET LEVELING COMMANDS ====================

    @commands.group(name="setleveling", invoke_without_command=True)
    @has_leveling_role()
    async def setleveling(self, ctx: commands.Context):
        """Konfigurasi leveling settings untuk server."""
        settings = self._get_leveling_settings(ctx.guild.id)

        description = "**Current Leveling Settings:**\n\n"
        description += f"📊 **Status:** {'Enabled' if settings.get('leveling_enabled') else 'Disabled'}\n"
        description += f"💰 **XP per Message:** {settings.get('xp_per_message')}\n"
        description += f"⏱️ **Cooldown:** {settings.get('cooldown_seconds')}s\n"
        description += f"📏 **Min. Karakter:** {settings.get('min_message_length', 0)}\n"

        level_up_channel = None
        if settings.get('level_up_channel_id'):
            level_up_channel = ctx.guild.get_channel(settings['level_up_channel_id'])

        description += f"📢 **Level Up Channel:** {level_up_channel.mention if level_up_channel else 'Current Channel'}\n"
        description += f"🔔 **Notifications:** {'Enabled' if settings.get('notify_level_up') else 'Disabled'}\n"

        embed = discord.Embed(
            title="⚙️ Leveling Configuration",
            description=description,
            color=config.COLORS["info"]
        )
        await ctx.send(embed=embed)

    @setleveling.command(name="toggle")
    async def leveling_toggle(self, ctx: commands.Context, enabled: bool):
        """Enable atau disable leveling."""
        if HAS_DATABASE:
            db.toggle_leveling(ctx.guild.id, enabled)

        status = "enabled" if enabled else "disabled"
        embed = self._create_embed(
            "✅ Leveling Settings",
            f"Leveling telah di-{status}!",
            config.COLORS["success"]
        )
        await ctx.send(embed=embed)

    @setleveling.command(name="xp")
    async def leveling_xp(self, ctx: commands.Context, amount: int):
        """Set XP amount per message (1-100)."""
        amount = max(1, min(100, amount))

        if HAS_DATABASE:
            settings = self._get_leveling_settings(ctx.guild.id)
            settings['xp_per_message'] = amount
            db.set_leveling_settings(ctx.guild.id, settings)

        embed = self._create_embed(
            "✅ XP Amount Set",
            f"Member sekarang akan mendapatkan **{amount} XP** per pesan.",
            config.COLORS["success"]
        )
        await ctx.send(embed=embed)

    @setleveling.command(name="cooldown")
    async def leveling_cooldown(self, ctx: commands.Context, seconds: int):
        """Set XP cooldown dalam detik (3-3600)."""
        seconds = max(3, min(3600, seconds))

        if HAS_DATABASE:
            settings = self._get_leveling_settings(ctx.guild.id)
            settings['cooldown_seconds'] = seconds
            db.set_leveling_settings(ctx.guild.id, settings)

        embed = self._create_embed(
            "✅ Cooldown Set",
            f"XP cooldown diatur ke **{seconds} detik**.",
            config.COLORS["success"]
        )
        await ctx.send(embed=embed)

    @setleveling.command(name="minlength")
    async def leveling_minlength(self, ctx: commands.Context, length: int):
        """Set minimum panjang pesan untuk dapat XP (0-2000)."""
        length = max(0, min(2000, length))

        if HAS_DATABASE:
            settings = self._get_leveling_settings(ctx.guild.id)
            settings['min_message_length'] = length
            db.set_leveling_settings(ctx.guild.id, settings)

        if length == 0:
            msg = "Minimum panjang pesan dihapus. Semua pesan akan mendapatkan XP."
        else:
            msg = f"Minimum panjang pesan diatur ke **{length} karakter**. Pesan lebih pendek dari itu tidak akan mendapatkan XP."

        embed = self._create_embed(
            "✅ Minimum Panjang Pesan Diatur",
            msg,
            config.COLORS["success"]
        )
        await ctx.send(embed=embed)

    @setleveling.command(name="channel")
    async def leveling_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Set channel untuk level up notifications."""
        channel_id = channel.id if channel else None

        if HAS_DATABASE:
            settings = self._get_leveling_settings(ctx.guild.id)
            settings['level_up_channel_id'] = channel_id
            db.set_leveling_settings(ctx.guild.id, settings)

        if channel:
            embed = self._create_embed(
                "✅ Channel Set",
                f"Level up notifications akan dikirim ke {channel.mention}",
                config.COLORS["success"]
            )
        else:
            embed = self._create_embed(
                "✅ Channel Reset",
                "Level up notifications akan dikirim ke channel saat ini.",
                config.COLORS["success"]
            )
        await ctx.send(embed=embed)

    @setleveling.command(name="notifications")
    async def leveling_notifications(self, ctx: commands.Context, enabled: bool):
        """Enable atau disable level up notifications."""
        if HAS_DATABASE:
            settings = self._get_leveling_settings(ctx.guild.id)
            settings['notify_level_up'] = 1 if enabled else 0
            db.set_leveling_settings(ctx.guild.id, settings)

        status = "enabled" if enabled else "disabled"
        embed = self._create_embed(
            "✅ Notifications Updated",
            f"Level up notifications {status}.",
            config.COLORS["success"]
        )
        await ctx.send(embed=embed)

    # ==================== LEVEL ROLE COMMANDS ====================

    @commands.group(name="levelrole", invoke_without_command=True)
    @has_leveling_role()
    @commands.has_permissions(manage_roles=True)
    async def levelrole(self, ctx: commands.Context):
        """Manage roles yang diberikan di level tertentu."""
        if not HAS_DATABASE:
            return await ctx.send("Database tidak tersedia.")

        roles = db.get_level_roles(ctx.guild.id)

        if not roles:
            embed = self._create_embed(
                "🎭 Level Roles",
                "Tidak ada level roles yang dikonfigurasi.\nGunakan `!levelrole add <level> <role>` untuk menambah.",
                config.COLORS["info"]
            )
            return await ctx.send(embed=embed)

        description = "**Level Roles:**\n\n"
        for entry in roles:
            role = ctx.guild.get_role(entry['role_id'])
            if role:
                stack = " (keeps previous)" if entry.get('role_stack') else ""
                description += f"**Level {entry['level']}:** {role.mention}{stack}\n"

        embed = discord.Embed(
            title="🎭 Level Roles",
            description=description,
            color=config.COLORS["info"]
        )
        await ctx.send(embed=embed)

    @levelrole.command(name="add")
    async def levelrole_add(self, ctx: commands.Context, level: int, role: discord.Role, stack: bool = False):
        """Tambah role reward untuk level tertentu."""
        if not HAS_DATABASE:
            return await ctx.send("Database tidak tersedia.")

        # Cek bot bisa assign role ini
        if role >= ctx.guild.me.top_role:
            embed = self._create_embed(
                "❌ Error",
                "Bot tidak bisa assign role yang sama atau lebih tinggi dari role bot!",
                config.COLORS["error"]
            )
            return await ctx.send(embed=embed)

        db.add_level_role(ctx.guild.id, level, role.id, stack)

        stack_text = " (akan keep previous roles)" if stack else ""
        embed = self._create_embed(
            "✅ Level Role Added",
            f"{role.mention} akan diberikan di **Level {level}**{stack_text}.",
            config.COLORS["success"]
        )
        await ctx.send(embed=embed)

    @levelrole.command(name="remove")
    async def levelrole_remove(self, ctx: commands.Context, level: int, role: discord.Role):
        """Hapus level role reward."""
        if not HAS_DATABASE:
            return await ctx.send("Database tidak tersedia.")

        db.remove_level_role(ctx.guild.id, level, role.id)

        embed = self._create_embed(
            "✅ Level Role Removed",
            f"{role.mention} dihapus dari Level {level} rewards.",
            config.COLORS["success"]
        )
        await ctx.send(embed=embed)

    # ==================== ADMIN COMMANDS ====================

    @commands.command(name="resetxp")
    @has_leveling_role()
    @commands.has_permissions(administrator=True)
    async def reset_xp(self, ctx: commands.Context, member: discord.Member):
        """Reset XP user (admin only)."""
        if not HAS_DATABASE:
            return await ctx.send("Database tidak tersedia.")

        db.reset_user_xp(ctx.guild.id, member.id)

        embed = self._create_embed(
            "✅ XP Reset",
            f"XP {member.mention} telah di-reset ke 0.",
            config.COLORS["success"]
        )
        await ctx.send(embed=embed)

    @commands.command(name="addxp")
    @has_leveling_role()
    @commands.has_permissions(administrator=True)
    async def add_xp(self, ctx: commands.Context, member: discord.Member, amount: int):
        """Tambah XP ke user (admin only)."""
        if not HAS_DATABASE:
            return await ctx.send("Database tidak tersedia.")

        current_data = self._get_user_xp(ctx.guild.id, member.id)
        old_level = current_data.get('current_level', 0)

        success, new_level, new_xp = db.add_user_xp(ctx.guild.id, member.id, amount)

        if success:
            # Cek level up
            xp_needed = xp_required_for_level(old_level + 1)
            if new_xp >= xp_needed:
                await self._check_level_up(member, ctx.guild.id, old_level, new_xp)

            total_xp = current_data.get('total_xp', 0) + amount
            embed = self._create_embed(
                "✅ XP Added",
                f"Menambahkan **{amount} XP** ke {member.mention}.\nLevel: **{new_level}** | XP: **{new_xp:,}**\nTotal XP: **{total_xp:,}**",
                config.COLORS["success"]
            )
            await ctx.send(embed=embed)
        else:
            embed = self._create_embed(
                "❌ Error",
                "Gagal menambahkan XP!",
                config.COLORS["error"]
            )
            await ctx.send(embed=embed)

    @commands.command(name="fixxp")
    @has_leveling_role()
    @commands.has_permissions(administrator=True)
    async def fix_xp(self, ctx: commands.Context, scope: str = "guild"):
        """
        Recalculate level dan XP untuk semua user.
        Usage: !fixxp [guild|all]
        - guild: Hanya untuk server ini (default)
        - all: Untuk semua server
        """
        if not HAS_DATABASE:
            return await ctx.send("Database tidak tersedia.")

        # Confirm with user
        if scope.lower() == "all":
            msg = await ctx.send("⚠️ **Peringatan**: Ini akan memperbaiki data untuk **SEMUA** server. Ketik `confirm` untuk melanjutkan.")

            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == "confirm"

            try:
                await self.bot.wait_for("message", check=check, timeout=30)
            except asyncio.TimeoutError:
                return await msg.edit(content="❌ Dibatalkan.")
        else:
            scope = "guild"

        # Show "working" message
        working_msg = await ctx.send("🔄 Memperbaiki data XP...")

        # Run recalculation
        guild_id = ctx.guild.id if scope == "guild" else None
        result = db.recalculate_all_user_levels(guild_id=guild_id)

        if result.get('success'):
            embed = self._create_embed(
                "✅ XP Data Fixed",
                f"Berhasil memperbaiki **{result.get('updated_count', 0)}** user!",
                config.COLORS["success"]
            )
            await working_msg.edit(content=None, embed=embed)
        else:
            embed = self._create_embed(
                "❌ Error",
                f"Gagal memperbaiki data: {result.get('error', 'Unknown error')}",
                config.COLORS["error"]
            )
            await working_msg.edit(content=None, embed=embed)

    # ==================== ERROR HANDLER ====================

    @level.error
    @leaderboard.error
    @setleveling.error
    @levelrole.error
    @reset_xp.error
    @add_xp.error
    @fix_xp.error
    async def leveling_error(self, ctx: commands.Context, error):
        """Handle leveling command errors."""
        if isinstance(error, commands.MissingRequiredArgument):
            embed = self._create_embed(
                "❌ Missing Argument",
                f"Argumen `{error.param.name}` diperlukan!",
                config.COLORS["error"]
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingPermissions):
            embed = self._create_embed(
                "❌ Missing Permissions",
                "Kamu tidak memiliki permission untuk command ini!",
                config.COLORS["error"]
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BadArgument):
            embed = self._create_embed(
                "❌ Invalid Argument",
                str(error),
                config.COLORS["error"]
            )
            await ctx.send(embed=embed)
        else:
            embed = self._create_embed(
                "❌ Error",
                f"Terjadi error: {str(error)}",
                config.COLORS["error"]
            )
            await ctx.send(embed=embed)


# ==================== SETUP FUNCTION ====================

async def setup(bot: commands.Bot):
    """Setup function untuk load cog."""
    await bot.add_cog(Leveling(bot))
