"""
Moderation Cog
==============
Commands untuk moderation server Discord.
"""

import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta
from typing import Optional, List
import config

# Import database (try/except in case dashboard not installed)
try:
    from dashboard.backend import database as db
    HAS_DATABASE = True
except ImportError:
    HAS_DATABASE = False


def get_mod_roles(guild_id: int) -> Optional[List[int]]:
    """Get moderation roles from database or config."""
    if HAS_DATABASE:
        roles = db.get_moderation_roles(guild_id)
        if roles:
            return roles
    
    # Fallback to config
    return config.MODERATION_ROLE_IDS


def has_mod_role():
    """Custom check for moderation role permission."""
    async def predicate(ctx: commands.Context) -> bool:
        # Server owner always has access
        if ctx.author.id == ctx.guild.owner_id:
            return True
        
        # Get allowed roles (from DB or config)
        allowed_roles = get_mod_roles(ctx.guild.id)
        
        # If None, use default Discord permissions
        if allowed_roles is None:
            return True  # Let the @commands.has_permissions handle it
        
        # If empty list, only owner can use
        if not allowed_roles:
            return False
        
        # Check if user has any of the allowed roles
        user_role_ids = [role.id for role in ctx.author.roles]
        return any(role_id in user_role_ids for role_id in allowed_roles)
    
    return commands.check(predicate)


class Moderation(commands.Cog):
    """Cog untuk moderation commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _create_embed(self, title: str, description: str, color: int) -> discord.Embed:
        """Helper untuk membuat embed."""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        embed.set_footer(text=f"Moderation Bot")
        return embed

    async def _log_action(self, guild: discord.Guild, embed: discord.Embed):
        """Log moderation action ke channel."""
        if config.MOD_LOG_CHANNEL_ID:
            channel = guild.get_channel(config.MOD_LOG_CHANNEL_ID)
            if channel:
                await channel.send(embed=embed)

    def _log_to_database(
        self,
        guild_id: int,
        action: str,
        user: discord.User,
        moderator: discord.User,
        reason: str = None,
        duration: str = None
    ):
        """Log moderation action ke database."""
        if HAS_DATABASE:
            db.add_moderation_log(
                guild_id=guild_id,
                action=action,
                user_id=user.id,
                user_name=str(user),
                moderator_id=moderator.id,
                moderator_name=str(moderator),
                reason=reason,
                duration=duration
            )

    # ==================== KICK COMMAND ====================
    @commands.command(name="kick")
    @has_mod_role()
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Tidak ada alasan"):
        """Kick member dari server."""
        if member.top_role >= ctx.author.top_role:
            embed = self._create_embed(
                "❌ Error",
                "Kamu tidak bisa kick member dengan role yang sama atau lebih tinggi!",
                config.COLORS["error"]
            )
            return await ctx.send(embed=embed)

        if member == ctx.author:
            embed = self._create_embed(
                "❌ Error",
                "Kamu tidak bisa kick dirimu sendiri!",
                config.COLORS["error"]
            )
            return await ctx.send(embed=embed)

        try:
            await member.kick(reason=f"{reason} | Oleh: {ctx.author}")
            embed = self._create_embed(
                "👢 Member Kicked",
                f"**{member}** telah di-kick dari server.\n**Alasan:** {reason}\n**Oleh:** {ctx.author.mention}",
                config.COLORS["warning"]
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await ctx.send(embed=embed)
            await self._log_action(ctx.guild, embed)
            self._log_to_database(ctx.guild.id, "kick", member, ctx.author, reason)
        except Exception as e:
            embed = self._create_embed(
                "❌ Error",
                f"Gagal kick member: {str(e)}",
                config.COLORS["error"]
            )
            await ctx.send(embed=embed)

    # ==================== BAN COMMAND ====================
    @commands.command(name="ban")
    @has_mod_role()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Tidak ada alasan"):
        """Ban member dari server."""
        if member.top_role >= ctx.author.top_role:
            embed = self._create_embed(
                "❌ Error",
                "Kamu tidak bisa ban member dengan role yang sama atau lebih tinggi!",
                config.COLORS["error"]
            )
            return await ctx.send(embed=embed)

        if member == ctx.author:
            embed = self._create_embed(
                "❌ Error",
                "Kamu tidak bisa ban dirimu sendiri!",
                config.COLORS["error"]
            )
            return await ctx.send(embed=embed)

        try:
            await member.ban(reason=f"{reason} | Oleh: {ctx.author}")
            embed = self._create_embed(
                "🔨 Member Banned",
                f"**{member}** telah di-ban dari server.\n**Alasan:** {reason}\n**Oleh:** {ctx.author.mention}",
                config.COLORS["error"]
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await ctx.send(embed=embed)
            await self._log_action(ctx.guild, embed)
            self._log_to_database(ctx.guild.id, "ban", member, ctx.author, reason)
        except Exception as e:
            embed = self._create_embed(
                "❌ Error",
                f"Gagal ban member: {str(e)}",
                config.COLORS["error"]
            )
            await ctx.send(embed=embed)

    # ==================== UNBAN COMMAND ====================
    @commands.command(name="unban")
    @has_mod_role()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user_id: int):
        """Unban user berdasarkan ID."""
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user)
            embed = self._create_embed(
                "✅ User Unbanned",
                f"**{user}** telah di-unban dari server.\n**Oleh:** {ctx.author.mention}",
                config.COLORS["success"]
            )
            await ctx.send(embed=embed)
            await self._log_action(ctx.guild, embed)
            self._log_to_database(ctx.guild.id, "unban", user, ctx.author)
        except discord.NotFound:
            embed = self._create_embed(
                "❌ Error",
                "User tidak ditemukan atau tidak di-ban.",
                config.COLORS["error"]
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = self._create_embed(
                "❌ Error",
                f"Gagal unban user: {str(e)}",
                config.COLORS["error"]
            )
            await ctx.send(embed=embed)

    # ==================== MUTE (TIMEOUT) COMMAND ====================
    @commands.command(name="mute", aliases=["timeout"])
    @has_mod_role()
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def mute(self, ctx: commands.Context, member: discord.Member, duration: int = None, *, reason: str = "Tidak ada alasan"):
        """
        Mute (timeout) member untuk durasi tertentu.
        Duration dalam menit. Default: 10 menit.
        """
        if duration is None:
            duration = config.DEFAULT_MUTE_DURATION

        if member.top_role >= ctx.author.top_role:
            embed = self._create_embed(
                "❌ Error",
                "Kamu tidak bisa mute member dengan role yang sama atau lebih tinggi!",
                config.COLORS["error"]
            )
            return await ctx.send(embed=embed)

        if member == ctx.author:
            embed = self._create_embed(
                "❌ Error",
                "Kamu tidak bisa mute dirimu sendiri!",
                config.COLORS["error"]
            )
            return await ctx.send(embed=embed)

        # Maximum timeout adalah 28 hari
        if duration > 40320:
            duration = 40320

        try:
            await member.timeout(timedelta(minutes=duration), reason=f"{reason} | Oleh: {ctx.author}")
            embed = self._create_embed(
                "🔇 Member Muted",
                f"**{member}** telah di-mute selama **{duration} menit**.\n**Alasan:** {reason}\n**Oleh:** {ctx.author.mention}",
                config.COLORS["warning"]
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await ctx.send(embed=embed)
            await self._log_action(ctx.guild, embed)
            self._log_to_database(ctx.guild.id, "mute", member, ctx.author, reason, f"{duration} menit")
        except Exception as e:
            embed = self._create_embed(
                "❌ Error",
                f"Gagal mute member: {str(e)}",
                config.COLORS["error"]
            )
            await ctx.send(embed=embed)

    # ==================== UNMUTE COMMAND ====================
    @commands.command(name="unmute", aliases=["untimeout"])
    @has_mod_role()
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def unmute(self, ctx: commands.Context, member: discord.Member):
        """Remove timeout dari member."""
        try:
            await member.timeout(None)
            embed = self._create_embed(
                "🔊 Member Unmuted",
                f"**{member}** telah di-unmute.\n**Oleh:** {ctx.author.mention}",
                config.COLORS["success"]
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await ctx.send(embed=embed)
            await self._log_action(ctx.guild, embed)
            self._log_to_database(ctx.guild.id, "unmute", member, ctx.author)
        except Exception as e:
            embed = self._create_embed(
                "❌ Error",
                f"Gagal unmute member: {str(e)}",
                config.COLORS["error"]
            )
            await ctx.send(embed=embed)

    # ==================== CLEAR/PURGE COMMAND ====================
    @commands.command(name="clear", aliases=["purge", "prune"])
    @has_mod_role()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context, amount: int = 10):
        """Hapus sejumlah pesan dari channel."""
        if amount < 1:
            embed = self._create_embed(
                "❌ Error",
                "Jumlah minimal adalah 1!",
                config.COLORS["error"]
            )
            return await ctx.send(embed=embed)

        if amount > 100:
            amount = 100

        try:
            deleted = await ctx.channel.purge(limit=amount + 1)  # +1 untuk command message
            embed = self._create_embed(
                "🗑️ Messages Cleared",
                f"Berhasil menghapus **{len(deleted) - 1}** pesan.\n**Oleh:** {ctx.author.mention}",
                config.COLORS["success"]
            )
            msg = await ctx.send(embed=embed)
            await msg.delete(delay=5)
        except Exception as e:
            embed = self._create_embed(
                "❌ Error",
                f"Gagal menghapus pesan: {str(e)}",
                config.COLORS["error"]
            )
            await ctx.send(embed=embed)

    # ==================== WARN COMMAND ====================
    @commands.command(name="warn")
    @has_mod_role()
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Tidak ada alasan"):
        """Warn member. (DM ke member)"""
        if member.bot:
            embed = self._create_embed(
                "❌ Error",
                "Kamu tidak bisa warn bot!",
                config.COLORS["error"]
            )
            return await ctx.send(embed=embed)

        try:
            # Kirim DM ke member
            dm_embed = self._create_embed(
                "⚠️ Warning",
                f"Kamu telah di-warn di **{ctx.guild.name}**\n**Alasan:** {reason}\n**Oleh:** {ctx.author}",
                config.COLORS["warning"]
            )
            dm_embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
            await member.send(embed=dm_embed)
        except:
            pass  # Ignore jika DM gagal

        embed = self._create_embed(
            "⚠️ Member Warned",
            f"**{member}** telah di-warn.\n**Alasan:** {reason}\n**Oleh:** {ctx.author.mention}",
            config.COLORS["warning"]
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)
        await self._log_action(ctx.guild, embed)
        self._log_to_database(ctx.guild.id, "warn", member, ctx.author, reason)

    # ==================== SLOWMODE COMMAND ====================
    @commands.command(name="slowmode")
    @has_mod_role()
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def slowmode(self, ctx: commands.Context, seconds: int = 0):
        """Set slowmode untuk channel (0 untuk disable)."""
        if seconds < 0:
            seconds = 0
        if seconds > 21600:  # Max 6 hours
            seconds = 21600

        try:
            await ctx.channel.edit(slowmode_delay=seconds)
            if seconds == 0:
                embed = self._create_embed(
                    "⏱️ Slowmode Disabled",
                    f"Slowmode telah dinonaktifkan di channel ini.\n**Oleh:** {ctx.author.mention}",
                    config.COLORS["success"]
                )
            else:
                embed = self._create_embed(
                    "⏱️ Slowmode Set",
                    f"Slowmode telah diatur ke **{seconds} detik**.\n**Oleh:** {ctx.author.mention}",
                    config.COLORS["info"]
                )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = self._create_embed(
                "❌ Error",
                f"Gagal mengatur slowmode: {str(e)}",
                config.COLORS["error"]
            )
            await ctx.send(embed=embed)

    # ==================== LOCK COMMAND ====================
    @commands.command(name="lock")
    @has_mod_role()
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def lock(self, ctx: commands.Context):
        """Lock channel (disable send messages untuk @everyone)."""
        try:
            await ctx.channel.set_permissions(
                ctx.guild.default_role,
                send_messages=False,
                reason=f"Channel locked by {ctx.author}"
            )
            embed = self._create_embed(
                "🔒 Channel Locked",
                f"Channel ini telah dikunci.\n**Oleh:** {ctx.author.mention}",
                config.COLORS["warning"]
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = self._create_embed(
                "❌ Error",
                f"Gagal mengunci channel: {str(e)}",
                config.COLORS["error"]
            )
            await ctx.send(embed=embed)

    # ==================== UNLOCK COMMAND ====================
    @commands.command(name="unlock")
    @has_mod_role()
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def unlock(self, ctx: commands.Context):
        """Unlock channel (enable send messages untuk @everyone)."""
        try:
            await ctx.channel.set_permissions(
                ctx.guild.default_role,
                send_messages=None,  # Reset to default
                reason=f"Channel unlocked by {ctx.author}"
            )
            embed = self._create_embed(
                "🔓 Channel Unlocked",
                f"Channel ini telah dibuka.\n**Oleh:** {ctx.author.mention}",
                config.COLORS["success"]
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = self._create_embed(
                "❌ Error",
                f"Gagal membuka channel: {str(e)}",
                config.COLORS["error"]
            )
            await ctx.send(embed=embed)

    # ==================== ERROR HANDLERS ====================
    @kick.error
    @ban.error
    @unban.error
    @mute.error
    @unmute.error
    @clear.error
    @warn.error
    @slowmode.error
    @lock.error
    @unlock.error
    async def moderation_error(self, ctx: commands.Context, error):
        """Handle moderation command errors."""
        if isinstance(error, commands.MissingPermissions):
            embed = self._create_embed(
                "❌ Permission Denied",
                "Kamu tidak memiliki permission untuk menggunakan command ini!",
                config.COLORS["error"]
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BotMissingPermissions):
            embed = self._create_embed(
                "❌ Bot Permission Error",
                "Bot tidak memiliki permission yang diperlukan!",
                config.COLORS["error"]
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MemberNotFound):
            embed = self._create_embed(
                "❌ Member Not Found",
                "Member tidak ditemukan!",
                config.COLORS["error"]
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = self._create_embed(
                "❌ Missing Argument",
                f"Argumen `{error.param.name}` diperlukan!",
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


async def setup(bot: commands.Bot):
    """Setup function untuk load cog."""
    await bot.add_cog(Moderation(bot))
