"""
Welcome Cog
===========
Handler untuk welcome dan goodbye member.
"""

import discord
from discord.ext import commands
from datetime import datetime
from typing import Optional, List
import io
import config

# Import image generator
try:
    from utils.welcome_image import generate_welcome_image, generate_goodbye_image, generate_animated_welcome_image, is_gif_url
    HAS_IMAGE_GEN = True
except ImportError:
    HAS_IMAGE_GEN = False

# Import database (try/except in case dashboard not installed)
try:
    from dashboard.backend import database as db
    HAS_DATABASE = True
except ImportError:
    HAS_DATABASE = False


def get_welcome_roles(guild_id: int) -> Optional[List[int]]:
    """Get welcome admin roles from database or config."""
    if HAS_DATABASE:
        roles = db.get_welcome_roles(guild_id)
        if roles:
            return roles
    
    # Fallback to config
    return config.WELCOME_ADMIN_ROLE_IDS


def get_guild_settings(guild_id: int) -> dict:
    """Get guild settings from database."""
    if HAS_DATABASE:
        settings = db.get_guild_settings(guild_id)
        if settings:
            return settings
    return {}


def has_welcome_role():
    """Custom check for welcome admin role permission."""
    async def predicate(ctx: commands.Context) -> bool:
        # Server owner always has access
        if ctx.author.id == ctx.guild.owner_id:
            return True
        
        # Get allowed roles (from DB or config)
        allowed_roles = get_welcome_roles(ctx.guild.id)
        
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


class Welcome(commands.Cog):
    """Cog untuk welcome member events dan commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Store welcome channel per guild (in-memory fallback)
        self.welcome_channels = {}  # guild_id -> channel_id
        self.auto_roles = {}  # guild_id -> role_id


    def _create_embed(self, title: str, description: str, color: int) -> discord.Embed:
        """Helper untuk membuat embed."""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        return embed

    def _format_message(self, template: str, member: discord.Member) -> str:
        """Format message template with placeholders."""
        if not template:
            return ""
        
        replacements = {
            "{user}": member.mention,
            "{username}": member.name,
            "{avatar}": member.display_avatar.url,
            "{server}": member.guild.name,
            "{member_count}": str(member.guild.member_count)
        }
        
        for placeholder, value in replacements.items():
            template = template.replace(placeholder, value)
            
        return template

    def _create_welcome_embed(self, member: discord.Member) -> discord.Embed:
        """Buat welcome embed yang cantik."""
        # Get settings
        settings = get_guild_settings(member.guild.id)

        # Get template or default
        template = settings.get('welcome_message')
        if not template:
            template = (
                f"Hai {member.mention}! Selamat datang di **{member.guild.name}**! 🎉\n\n"
                f"Kamu adalah member ke-**{member.guild.member_count}**!\n"
                f"Semoga betah dan enjoy di server ini!"
            )
        else:
            template = self._format_message(template, member)

        embed = discord.Embed(
            description=template,
            color=config.COLORS["welcome"]
        )

        embed.set_author(
            name=f"{member.name} joined the server!",
            icon_url=member.display_avatar.url
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        if member.guild.icon:
            embed.set_footer(
                text=member.guild.name,
                icon_url=member.guild.icon.url
            )
        else:
            embed.set_footer(text=member.guild.name)

        # Add banner if configured
        banner_url = settings.get('banner_url')
        if banner_url:
            embed.set_image(url=banner_url)

        return embed

    def _create_goodbye_embed(self, member: discord.Member) -> discord.Embed:
        """Buat goodbye embed."""
        # Get settings
        settings = get_guild_settings(member.guild.id)

        # Get template or default
        template = settings.get('goodbye_message')
        if not template:
            template = (
                f"**{member.name}** telah meninggalkan server.\n"
                f"Sekarang kita memiliki **{member.guild.member_count}** member."
            )
        else:
            template = self._format_message(template, member)

        embed = discord.Embed(
            description=template,
            color=config.COLORS["error"],
            timestamp=datetime.utcnow()
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        if member.guild.icon:
            embed.set_footer(
                text=member.guild.name,
                icon_url=member.guild.icon.url
            )

        # Add banner if configured
        banner_url = settings.get('banner_url')
        if banner_url:
            embed.set_image(url=banner_url)

        return embed

    def _get_welcome_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """Get welcome channel untuk guild."""
        # Check database first
        settings = get_guild_settings(guild.id)
        if settings and settings.get('welcome_channel_id'):
            channel_id = int(settings['welcome_channel_id'])  # Convert to int
            channel = guild.get_channel(channel_id)
            if channel:
                return channel
        
        # Check stored channel (in-memory)
        channel_id = self.welcome_channels.get(guild.id)
        if channel_id:
            channel = guild.get_channel(channel_id)
            if channel:
                return channel
        
        # Fallback to config
        if config.WELCOME_CHANNEL_ID:
            channel = guild.get_channel(config.WELCOME_CHANNEL_ID)
            if channel:
                return channel
        
        # Try to find a channel named "welcome" or similar
        for channel in guild.text_channels:
            if "welcome" in channel.name.lower() or "greet" in channel.name.lower():
                return channel

        # Last resort: system channel
        return guild.system_channel

    def _get_goodbye_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """Get goodbye channel untuk guild."""
        # Check database first
        settings = get_guild_settings(guild.id)
        if settings and settings.get('goodbye_channel_id'):
            channel_id = int(settings['goodbye_channel_id'])  # Convert to int
            channel = guild.get_channel(channel_id)
            if channel:
                return channel

        # Check stored channel (in-memory)
        channel_id = self.goodbye_channels.get(guild.id)
        if channel_id:
            channel = guild.get_channel(channel_id)
            if channel:
                return channel

        # Fallback to config
        if config.GOODBYE_CHANNEL_ID:
            channel = guild.get_channel(config.GOODBYE_CHANNEL_ID)
            if channel:
                return channel

        # Try to find a channel named "goodbye" or similar
        for channel in guild.text_channels:
            if "goodbye" in channel.name.lower() or "leave" in channel.name.lower() or "farewell" in channel.name.lower():
                return channel

        # Last resort: system channel
        return guild.system_channel

    def _get_auto_roles(self, guild: discord.Guild) -> list[discord.Role]:
        """Get multiple auto-assign roles untuk guild."""
        roles = []

        # Check database first for new auto_role_ids (multi-select)
        settings = get_guild_settings(guild.id)
        if settings and settings.get('auto_role_ids'):
            auto_role_ids = settings['auto_role_ids']
            if isinstance(auto_role_ids, list):
                for role_id in auto_role_ids:
                    role = guild.get_role(int(role_id) if isinstance(role_id, str) else role_id)
                    if role:
                        roles.append(role)

        # Fallback to old auto_role_id for backward compatibility
        if not roles and settings and settings.get('auto_role_id'):
            role = guild.get_role(settings['auto_role_id'])
            if role:
                roles.append(role)

        # Check in-memory or config
        if not roles:
            role_id = self.auto_roles.get(guild.id) or config.DEFAULT_ROLE_ID
            if role_id:
                role = guild.get_role(role_id)
                if role:
                    roles.append(role)

        return roles

    # ==================== EVENTS ====================
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Event handler saat member join."""
        if member.bot:
            return

        # Get welcome channel
        channel = self._get_welcome_channel(member.guild)

        if channel:
            # Check if we should use image
            settings = get_guild_settings(member.guild.id)
            use_image = settings.get('use_image', 0) if settings else 0
            send_gif_as_is = settings.get('send_gif_as_is', 0) if settings else 0
            send_banner_as_is = settings.get('send_banner_as_is', 0) if settings else 0
            banner_url = settings.get('banner_url')
            banner_file_path = settings.get('banner_file_path')

            print(f"[Welcome] use_image: {use_image}, send_gif_as_is: {send_gif_as_is}, send_banner_as_is: {send_banner_as_is}, HAS_IMAGE_GEN: {HAS_IMAGE_GEN}")

            # Check if welcome is enabled
            welcome_enabled = settings.get('welcome_enabled', 0) if settings else 0
            if not welcome_enabled:
                print(f"[Welcome] Welcome messages disabled for guild {member.guild.id}")
                return

            # Get welcome message (define early for both blocks)
            welcome_message = settings.get('welcome_message', '')
            if not welcome_message:
                welcome_message = "Welcome {user} to the server!"
            welcome_message = self._format_message(welcome_message, member)

            # Determine which banner to use
            actual_banner_url = banner_file_path if banner_file_path else banner_url

            # Check if send_banner_as_is mode (for custom Canva designs)
            if send_banner_as_is and actual_banner_url:
                from utils.welcome_image import download_image
                try:
                    print(f"[Welcome] Sending banner as-is: {actual_banner_url}")
                    banner_data = await download_image(actual_banner_url)
                    if banner_data:
                        print(f"[Welcome] Banner downloaded: {len(banner_data)} bytes")
                        # Determine file extension
                        ext = '.png'
                        if actual_banner_url.lower().endswith(('.jpg', '.jpeg')):
                            ext = '.jpg'
                        elif actual_banner_url.lower().endswith('.gif'):
                            ext = '.gif'
                        elif actual_banner_url.lower().endswith('.webp'):
                            ext = '.webp'

                        file = discord.File(io.BytesIO(banner_data), filename=f"welcome{ext}")
                        await channel.send(content=welcome_message, file=file)
                        return
                except Exception as e:
                    print(f"[Welcome] Banner as-is error: {e}")
                    import traceback
                    traceback.print_exc()

            # Check if GIF mode should be used
            use_gif_mode = False
            if send_gif_as_is and actual_banner_url:
                from utils.welcome_image import is_gif_url
                try:
                    use_gif_mode = await is_gif_url(actual_banner_url)
                    print(f"[Welcome] GIF mode: {use_gif_mode}")
                except:
                    pass

            if use_gif_mode:
                # Send GIF as-is (animated) with template message
                try:
                    from utils.welcome_image import download_gif_as_is
                    print(f"[Welcome] Downloading GIF as-is: {actual_banner_url}")
                    gif_data = await download_gif_as_is(actual_banner_url)
                    if gif_data:
                        print(f"[Welcome] GIF downloaded: {len(gif_data)} bytes")
                        # Determine extension
                        ext = '.gif' if actual_banner_url.lower().endswith('.gif') else '.gif'
                        filename = f"welcome{ext}"
                        file = discord.File(io.BytesIO(gif_data), filename=filename)
                        await channel.send(content=welcome_message, file=file)
                    else:
                        await channel.send(content=f"{welcome_message}\n{actual_banner_url}")
                except Exception as e:
                    print(f"[Welcome] GIF error: {e}")
                    await channel.send(content=welcome_message)
            elif use_image and HAS_IMAGE_GEN:
                # Generate welcome image
                try:
                    print("[Welcome] Generating welcome image...")
                    # Debug: print offset values
                    print(f"[Welcome] text_offset_x: {settings.get('text_offset_x', 0)}, text_offset_y: {settings.get('text_offset_y', 0)}")
                    print(f"[Welcome] avatar_offset_x: {settings.get('avatar_offset_x', 0)}, avatar_offset_y: {settings.get('avatar_offset_y', 0)}")

                    # Check if we should use animated GIF
                    use_animated_gif = settings.get('send_gif_as_is', 0) == 1 and actual_banner_url and actual_banner_url.lower().endswith('.gif')
                    image_bytes = None
                    filename = "welcome.png"

                    if use_animated_gif:
                        print("[Welcome] Using animated GIF mode")
                        image_bytes = await generate_animated_welcome_image(
                            avatar_url=str(member.display_avatar.url),
                            username=member.name,
                            banner_url=actual_banner_url,
                            welcome_text=settings.get('welcome_text', 'WELCOME'),
                            profile_position=settings.get('profile_position', 'center'),
                            text_color=settings.get('text_color', '#FFD700'),
                            font_family=settings.get('font_family', 'arial'),
                            banner_offset_x=settings.get('banner_offset_x', 0),
                            banner_offset_y=settings.get('banner_offset_y', 0),
                            avatar_offset_x=settings.get('avatar_offset_x', 0),
                            avatar_offset_y=settings.get('avatar_offset_y', 0),
                            text_offset_x=settings.get('text_offset_x', 0),
                            text_offset_y=settings.get('text_offset_y', 0),
                            welcome_text_size=settings.get('welcome_text_size', 56),
                            username_text_size=settings.get('username_text_size', 32),
                            avatar_size=settings.get('avatar_size', 180),
                            avatar_shape=settings.get('avatar_shape', 'circle'),
                            avatar_border_enabled=settings.get('avatar_border_enabled', True),
                            avatar_border_width=settings.get('avatar_border_width', 6),
                            avatar_border_color=settings.get('avatar_border_color', '#FFFFFF')
                        )
                        filename = "welcome.gif"

                    if not image_bytes:
                        image_bytes = await generate_welcome_image(
                            avatar_url=str(member.display_avatar.url),
                            username=member.name,
                            banner_url=actual_banner_url,
                            welcome_text=settings.get('welcome_text', 'WELCOME'),
                            profile_position=settings.get('profile_position', 'center'),
                            text_color=settings.get('text_color', '#FFD700'),
                            font_family=settings.get('font_family', 'arial'),
                            banner_offset_x=settings.get('banner_offset_x', 0),
                            banner_offset_y=settings.get('banner_offset_y', 0),
                            avatar_offset_x=settings.get('avatar_offset_x', 0),
                            avatar_offset_y=settings.get('avatar_offset_y', 0),
                            text_offset_x=settings.get('text_offset_x', 0),
                            text_offset_y=settings.get('text_offset_y', 0),
                            welcome_text_size=settings.get('welcome_text_size', 56),
                            username_text_size=settings.get('username_text_size', 32),
                            avatar_size=settings.get('avatar_size', 180),
                            avatar_shape=settings.get('avatar_shape', 'circle'),
                            avatar_border_enabled=settings.get('avatar_border_enabled', True),
                            avatar_border_width=settings.get('avatar_border_width', 6),
                            avatar_border_color=settings.get('avatar_border_color', '#FFFFFF')
                        )

                    if image_bytes:
                        print(f"[Welcome] Image generated successfully: {len(image_bytes)} bytes")
                        file = discord.File(io.BytesIO(image_bytes), filename=filename)
                        await channel.send(content=welcome_message, file=file)
                    else:
                        print("[Welcome] Image generation returned None")
                        await channel.send(content=welcome_message)
                except Exception as e:
                    print(f"[Welcome] Error: {e}")
                    import traceback
                    traceback.print_exc()
                    await channel.send(content=welcome_message)
            else:
                # Use plain text with banner image if available
                print("[Welcome] Using plain text mode")
                if actual_banner_url:
                    try:
                        from utils.welcome_image import download_image
                        print(f"[Welcome] Downloading banner: {actual_banner_url}")
                        banner_data = await download_image(actual_banner_url)
                        if banner_data:
                            print(f"[Welcome] Banner downloaded: {len(banner_data)} bytes")
                            file = discord.File(io.BytesIO(banner_data), filename="banner.png")
                            await channel.send(content=welcome_message, file=file)
                        else:
                            await channel.send(content=f"{welcome_message}\n{actual_banner_url}")
                    except Exception as e:
                        print(f"[Welcome] Banner error: {e}")
                        await channel.send(content=welcome_message)
                else:
                    await channel.send(content=welcome_message)

        # Auto-assign roles
        roles = self._get_auto_roles(member.guild)

        if roles:
            try:
                await member.add_roles(*roles, reason="Auto-role on join")
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Event handler saat member leave."""
        if member.bot:
            return

        channel = self._get_goodbye_channel(member.guild)

        if channel:
            # Check if we should use image
            settings = get_guild_settings(member.guild.id)

            # Check if goodbye is enabled
            goodbye_enabled = settings.get('goodbye_enabled', 0) if settings else 0
            if not goodbye_enabled:
                print(f"[Goodbye] Goodbye messages disabled for guild {member.guild.id}")
                return

            # Check for goodbye-specific image setting first
            use_goodbye_image = settings.get('use_goodbye_image', 0) if settings else 0
            use_image = settings.get('use_image', 0) if settings else 0

            # Use goodbye image settings if enabled, otherwise fallback to shared settings
            will_use_image = use_goodbye_image or use_image

            print(f"[Goodbye] use_goodbye_image: {use_goodbye_image}, use_image: {use_image}, will_use_image: {will_use_image}, HAS_IMAGE_GEN: {HAS_IMAGE_GEN}")

            # Get goodbye template (define early for both blocks)
            goodbye_message = settings.get('goodbye_message', '')
            if not goodbye_message:
                goodbye_message = "Goodbye {user}!"
            goodbye_message = self._format_message(goodbye_message, member)

            # Determine which settings to use (goodbye-specific or fallback to shared)
            if use_goodbye_image:
                # Use goodbye-specific settings
                banner_url = settings.get('goodbye_banner_url') or settings.get('banner_url')
                banner_file_path = settings.get('goodbye_banner_file_path') or settings.get('banner_file_path')
                actual_banner_url = banner_file_path if banner_file_path else banner_url
                send_gif_as_is = settings.get('goodbye_send_gif_as_is', 0)
                goodbye_text_val = settings.get('goodbye_text', 'GOODBYE')
                profile_position = settings.get('goodbye_profile_position', 'center')
                text_color = settings.get('goodbye_text_color', '#FF6B6B')
                font_family = settings.get('goodbye_font_family', 'arial')
                banner_offset_x = settings.get('goodbye_banner_offset_x', 0)
                banner_offset_y = settings.get('goodbye_banner_offset_y', 0)
                avatar_offset_x = settings.get('goodbye_avatar_offset_x', 0)
                avatar_offset_y = settings.get('goodbye_avatar_offset_y', 0)
                text_offset_x = settings.get('goodbye_text_offset_x', 0)
                text_offset_y = settings.get('goodbye_text_offset_y', 0)
            else:
                # Fallback to shared settings
                banner_url = settings.get('banner_url')
                banner_file_path = settings.get('banner_file_path')
                actual_banner_url = banner_file_path if banner_file_path else banner_url
                send_gif_as_is = settings.get('send_gif_as_is', 0)
                goodbye_text_val = settings.get('goodbye_text', 'GOODBYE')
                profile_position = settings.get('profile_position', 'center')
                text_color = settings.get('text_color', '#FF6B6B')
                font_family = settings.get('font_family', 'arial')
                banner_offset_x = settings.get('banner_offset_x', 0)
                banner_offset_y = settings.get('banner_offset_y', 0)
                avatar_offset_x = settings.get('avatar_offset_x', 0)
                avatar_offset_y = settings.get('avatar_offset_y', 0)
                text_offset_x = settings.get('text_offset_x', 0)
                text_offset_y = settings.get('text_offset_y', 0)

            # Check if GIF mode should be used (animated compositing)
            use_animated_gif = send_gif_as_is and actual_banner_url and actual_banner_url.lower().endswith('.gif')

            if use_animated_gif:
                # Generate animated goodbye image
                try:
                    print("[Goodbye] Generating animated goodbye image...")
                    image_bytes = await generate_animated_welcome_image(
                        avatar_url=str(member.display_avatar.url),
                        username=member.name,
                        banner_url=actual_banner_url,
                        welcome_text=goodbye_text_val,
                        profile_position=profile_position,
                        text_color=text_color,
                        font_family=font_family,
                        banner_offset_x=banner_offset_x,
                        banner_offset_y=banner_offset_y,
                        avatar_offset_x=avatar_offset_x,
                        avatar_offset_y=avatar_offset_y,
                        text_offset_x=text_offset_x,
                        text_offset_y=text_offset_y,
                        welcome_text_size=settings.get('welcome_text_size', 56),
                        username_text_size=settings.get('username_text_size', 32),
                        avatar_size=settings.get('avatar_size', 180)
                    )

                    if image_bytes:
                        print(f"[Goodbye] Animated GIF generated: {len(image_bytes)} bytes")
                        file = discord.File(io.BytesIO(image_bytes), filename="goodbye.gif")
                        await channel.send(content=goodbye_message, file=file)
                    else:
                        print("[Goodbye] Animated GIF generation failed, falling back to static")
                        # Fall through to static image generation
                        use_animated_gif = False
                except Exception as e:
                    print(f"[Goodbye] Animated GIF error: {e}")
                    import traceback
                    traceback.print_exc()
                    use_animated_gif = False

            if not use_animated_gif and will_use_image and HAS_IMAGE_GEN:
                # Generate goodbye image
                try:
                    print("[Goodbye] Generating goodbye image...")
                    image_bytes = await generate_goodbye_image(
                        avatar_url=str(member.display_avatar.url),
                        username=member.name,
                        banner_url=actual_banner_url,
                        goodbye_text=goodbye_text_val,
                        profile_position=profile_position,
                        text_color=text_color,
                        font_family=font_family,
                        banner_offset_x=banner_offset_x,
                        banner_offset_y=banner_offset_y,
                        avatar_offset_x=avatar_offset_x,
                        avatar_offset_y=avatar_offset_y,
                        text_offset_x=text_offset_x,
                        text_offset_y=text_offset_y,
                        welcome_text_size=settings.get('goodbye_welcome_text_size', 56),
                        username_text_size=settings.get('goodbye_username_text_size', 32),
                        avatar_size=settings.get('goodbye_avatar_size', 180),
                        avatar_shape=settings.get('goodbye_avatar_shape', 'circle'),
                        avatar_border_enabled=settings.get('goodbye_avatar_border_enabled', True),
                        avatar_border_width=settings.get('goodbye_avatar_border_width', 6),
                        avatar_border_color=settings.get('goodbye_avatar_border_color', '#FFFFFF')
                    )

                    # Debug print

                    if image_bytes:
                        print(f"[Goodbye] Image generated: {len(image_bytes)} bytes")
                        file = discord.File(io.BytesIO(image_bytes), filename="goodbye.png")
                        await channel.send(content=goodbye_message, file=file)
                    else:
                        print("[Goodbye] Image generation returned None")
                        await channel.send(content=goodbye_message)
                except Exception as e:
                    print(f"[Goodbye] Error: {e}")
                    import traceback
                    traceback.print_exc()
                    await channel.send(content=goodbye_message)
            else:
                # Use plain text with banner image if available
                print("[Goodbye] Using plain text mode")
                if actual_banner_url:
                    try:
                        from utils.welcome_image import download_image
                        print(f"[Goodbye] Downloading banner: {actual_banner_url}")
                        banner_data = await download_image(actual_banner_url)
                        if banner_data:
                            print(f"[Goodbye] Banner downloaded: {len(banner_data)} bytes")
                            file = discord.File(io.BytesIO(banner_data), filename="banner.png")
                            await channel.send(content=goodbye_message, file=file)
                        else:
                            await channel.send(content=f"{goodbye_message}\n{actual_banner_url}")
                    except Exception as e:
                        print(f"[Goodbye] Banner error: {e}")
                        await channel.send(content=goodbye_message)
                else:
                    await channel.send(content=goodbye_message)

    # ==================== COMMANDS ====================
    @commands.command(name="setwelcome")
    @has_welcome_role()
    @commands.has_permissions(manage_guild=True)
    async def set_welcome(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Set channel untuk welcome messages."""
        if channel is None:
            channel = ctx.channel

        self.welcome_channels[ctx.guild.id] = channel.id

        embed = self._create_embed(
            "✅ Welcome Channel Set",
            f"Welcome channel telah diset ke {channel.mention}",
            config.COLORS["success"]
        )
        await ctx.send(embed=embed)

    @commands.command(name="testwelcome")
    @has_welcome_role()
    @commands.has_permissions(manage_guild=True)
    async def test_welcome(self, ctx: commands.Context):
        """Test welcome message dengan dirimu sendiri."""
        settings = get_guild_settings(ctx.guild.id)
        print(f"[TEST] All settings: {settings}")
        use_image = settings.get('use_image', 0) if settings else 0
        send_gif_as_is = settings.get('send_gif_as_is', 0) if settings else 0
        send_banner_as_is = settings.get('send_banner_as_is', 0) if settings else 0
        banner_url = settings.get('banner_url')
        banner_file_path = settings.get('banner_file_path')

        actual_banner_url = banner_file_path if banner_file_path else banner_url

        # Get welcome template
        welcome_message = settings.get('welcome_message', '')
        if not welcome_message:
            welcome_message = "Welcome {user} to the server!"
        welcome_message = self._format_message(welcome_message, ctx.author)
        print(f"[TEST] Template: {welcome_message}")

        # Check if send_banner_as_is mode (for custom Canva designs)
        if send_banner_as_is and actual_banner_url:
            from utils.welcome_image import download_image
            try:
                banner_data = await download_image(actual_banner_url)
                if banner_data:
                    # Determine file extension
                    ext = '.png'
                    if actual_banner_url.lower().endswith(('.jpg', '.jpeg')):
                        ext = '.jpg'
                    elif actual_banner_url.lower().endswith('.gif'):
                        ext = '.gif'
                    elif actual_banner_url.lower().endswith('.webp'):
                        ext = '.webp'

                    file = discord.File(io.BytesIO(banner_data), filename=f"welcome{ext}")
                    await ctx.send(content=welcome_message, file=file)
                    return
            except Exception as e:
                print(f"[TEST] Error sending banner as-is: {e}")

        # Check if animated GIF compositing should be used
        use_animated_gif = send_gif_as_is and actual_banner_url and actual_banner_url.lower().endswith('.gif')

        # Get image settings for both animated and static modes
        profile_position = settings.get('profile_position', 'center') if settings else 'center'
        text_color = settings.get('text_color', '#FFD700') if settings else '#FFD700'
        font_family = settings.get('font_family', 'arial') if settings else 'arial'
        banner_offset_x = settings.get('banner_offset_x', 0) if settings else 0
        banner_offset_y = settings.get('banner_offset_y', 0) if settings else 0
        avatar_offset_x = settings.get('avatar_offset_x', 0) if settings else 0
        avatar_offset_y = settings.get('avatar_offset_y', 0) if settings else 0
        text_offset_x = settings.get('text_offset_x', 0) if settings else 0
        text_offset_y = settings.get('text_offset_y', 0) if settings else 0
        # Avatar settings
        avatar_shape = settings.get('avatar_shape', 'circle') if settings else 'circle'
        avatar_border_enabled = settings.get('avatar_border_enabled', True) if settings else True
        avatar_border_width = settings.get('avatar_border_width', 6) if settings else 6

        if use_animated_gif:
            # Generate animated welcome image with compositing
            print("[TEST] Generating animated welcome image...")
            image_bytes = await generate_animated_welcome_image(
                avatar_url=str(ctx.author.display_avatar.url),
                username=ctx.author.name,
                banner_url=actual_banner_url,
                welcome_text=settings.get('welcome_text', 'WELCOME'),
                profile_position=profile_position,
                text_color=text_color,
                font_family=font_family,
                banner_offset_x=banner_offset_x,
                banner_offset_y=banner_offset_y,
                avatar_offset_x=avatar_offset_x,
                avatar_offset_y=avatar_offset_y,
                text_offset_x=text_offset_x,
                text_offset_y=text_offset_y,
                welcome_text_size=settings.get('welcome_text_size', 56),
                username_text_size=settings.get('username_text_size', 32),
                avatar_size=settings.get('avatar_size', 180),
                avatar_shape=avatar_shape,
                avatar_border_enabled=avatar_border_enabled,
                avatar_border_width=avatar_border_width,
                avatar_border_color=settings.get('avatar_border_color', '#FFFFFF')
            )

            if image_bytes:
                file = discord.File(io.BytesIO(image_bytes), filename="welcome.gif")
                await ctx.send(content=welcome_message, file=file)
            else:
                await ctx.send("Failed to generate animated GIF. Check console for errors.")
        elif use_image and HAS_IMAGE_GEN:
            # Use static image mode
            image_bytes = await generate_welcome_image(
                avatar_url=str(ctx.author.display_avatar.url),
                username=ctx.author.name,
                banner_url=actual_banner_url,
                welcome_text=settings.get('welcome_text', 'WELCOME'),
                profile_position=profile_position,
                text_color=text_color,
                font_family=font_family,
                banner_offset_x=banner_offset_x,
                banner_offset_y=banner_offset_y,
                avatar_offset_x=avatar_offset_x,
                avatar_offset_y=avatar_offset_y,
                text_offset_x=text_offset_x,
                text_offset_y=text_offset_y,
                welcome_text_size=settings.get('welcome_text_size', 56),
                username_text_size=settings.get('username_text_size', 32),
                avatar_size=settings.get('avatar_size', 180),
                avatar_shape=avatar_shape,
                avatar_border_enabled=avatar_border_enabled,
                avatar_border_width=avatar_border_width,
                avatar_border_color=settings.get('avatar_border_color', '#FFFFFF')
            )

            if image_bytes:
                file = discord.File(io.BytesIO(image_bytes), filename="welcome.png")
                await ctx.send(content=welcome_message, file=file)
            else:
                await ctx.send(content=welcome_message)
        else:
            # Use plain text with banner image if available
            banner_url = settings.get('banner_url')
            if banner_url:
                try:
                    from utils.welcome_image import download_image
                    banner_data = await download_image(banner_url)
                    if banner_data:
                        file = discord.File(io.BytesIO(banner_data), filename="banner.png")
                        await ctx.send(content=welcome_message, file=file)
                    else:
                        await ctx.send(content=f"{welcome_message}\n{banner_url}")
                except:
                    await ctx.send(content=welcome_message)
            else:
                await ctx.send(content=welcome_message)

    @commands.command(name="testgoodbye")
    @has_welcome_role()
    @commands.has_permissions(manage_guild=True)
    async def test_goodbye(self, ctx: commands.Context):
        """Test goodbye message dengan dirimu sendiri."""
        settings = get_guild_settings(ctx.guild.id)

        # Check for goodbye-specific image setting first
        use_goodbye_image = settings.get('use_goodbye_image', 0) if settings else 0
        use_image = settings.get('use_image', 0) if settings else 0
        will_use_image = use_goodbye_image or use_image

        # Get goodbye template
        goodbye_message = settings.get('goodbye_message', '')
        if not goodbye_message:
            goodbye_message = "Goodbye {user}!"
        goodbye_message = self._format_message(goodbye_message, ctx.author)

        # Determine which settings to use (goodbye-specific or fallback to shared)
        if use_goodbye_image:
            banner_url = settings.get('goodbye_banner_url') or settings.get('banner_url')
            banner_file_path = settings.get('goodbye_banner_file_path') or settings.get('banner_file_path')
            actual_banner_url = banner_file_path if banner_file_path else banner_url
            send_gif_as_is = settings.get('goodbye_send_gif_as_is', 0)
            goodbye_text_val = settings.get('goodbye_text', 'GOODBYE')
            profile_position = settings.get('goodbye_profile_position', 'center')
            text_color = settings.get('goodbye_text_color', '#FF6B6B')
            font_family = settings.get('goodbye_font_family', 'arial')
            banner_offset_x = settings.get('goodbye_banner_offset_x', 0)
            banner_offset_y = settings.get('goodbye_banner_offset_y', 0)
            avatar_offset_x = settings.get('goodbye_avatar_offset_x', 0)
            avatar_offset_y = settings.get('goodbye_avatar_offset_y', 0)
            text_offset_x = settings.get('goodbye_text_offset_x', 0)
            text_offset_y = settings.get('goodbye_text_offset_y', 0)
        else:
            banner_url = settings.get('banner_url')
            banner_file_path = settings.get('banner_file_path')
            actual_banner_url = banner_file_path if banner_file_path else banner_url
            send_gif_as_is = settings.get('send_gif_as_is', 0)
            goodbye_text_val = settings.get('goodbye_text', 'GOODBYE')
            profile_position = settings.get('profile_position', 'center')
            text_color = settings.get('text_color', '#FF6B6B')
            font_family = settings.get('font_family', 'arial')
            banner_offset_x = settings.get('banner_offset_x', 0)
            banner_offset_y = settings.get('banner_offset_y', 0)
            avatar_offset_x = settings.get('avatar_offset_x', 0)
            avatar_offset_y = settings.get('avatar_offset_y', 0)
            text_offset_x = settings.get('text_offset_x', 0)
            text_offset_y = settings.get('text_offset_y', 0)

        # Check if animated GIF compositing should be used
        use_animated_gif = send_gif_as_is and actual_banner_url and actual_banner_url.lower().endswith('.gif')

        if use_animated_gif:
            # Generate animated goodbye image with compositing
            print("[TEST] Generating animated goodbye image...")
            image_bytes = await generate_animated_welcome_image(
                avatar_url=str(ctx.author.display_avatar.url),
                username=ctx.author.name,
                banner_url=actual_banner_url,
                welcome_text=goodbye_text_val,
                profile_position=profile_position,
                text_color=text_color,
                font_family=font_family,
                banner_offset_x=banner_offset_x,
                banner_offset_y=banner_offset_y,
                avatar_offset_x=avatar_offset_x,
                avatar_offset_y=avatar_offset_y,
                text_offset_x=text_offset_x,
                text_offset_y=text_offset_y,
                welcome_text_size=settings.get('welcome_text_size', 56),
                username_text_size=settings.get('username_text_size', 32),
                avatar_size=settings.get('avatar_size', 180)
            )

            if image_bytes:
                file = discord.File(io.BytesIO(image_bytes), filename="goodbye.gif")
                await ctx.send(content=goodbye_message, file=file)
            else:
                await ctx.send("Failed to generate animated GIF. Check console for errors.")
        elif will_use_image and HAS_IMAGE_GEN:
            # Use image mode
            image_bytes = await generate_goodbye_image(
                avatar_url=str(ctx.author.display_avatar.url),
                username=ctx.author.name,
                banner_url=actual_banner_url,
                goodbye_text=goodbye_text_val,
                profile_position=profile_position,
                text_color=text_color,
                font_family=font_family,
                banner_offset_x=banner_offset_x,
                banner_offset_y=banner_offset_y,
                avatar_offset_x=avatar_offset_x,
                avatar_offset_y=avatar_offset_y,
                text_offset_x=text_offset_x,
                text_offset_y=text_offset_y,
                welcome_text_size=settings.get('goodbye_welcome_text_size', 56),
                username_text_size=settings.get('goodbye_username_text_size', 32),
                avatar_size=settings.get('goodbye_avatar_size', 180),
                avatar_shape=settings.get('goodbye_avatar_shape', 'circle'),
                avatar_border_enabled=settings.get('goodbye_avatar_border_enabled', True),
                avatar_border_width=settings.get('goodbye_avatar_border_width', 6),
                avatar_border_color=settings.get('goodbye_avatar_border_color', '#FFFFFF')
            )

            # Debug print

            if image_bytes:
                file = discord.File(io.BytesIO(image_bytes), filename="goodbye.png")
                await ctx.send(content=goodbye_message, file=file)
            else:
                await ctx.send(content=goodbye_message)
        else:
            # Use plain text with banner image if available
            if actual_banner_url:
                try:
                    from utils.welcome_image import download_image
                    banner_data = await download_image(actual_banner_url)
                    if banner_data:
                        file = discord.File(io.BytesIO(banner_data), filename="banner.png")
                        await ctx.send(content=goodbye_message, file=file)
                    else:
                        await ctx.send(content=f"{goodbye_message}\n{actual_banner_url}")
                except:
                    await ctx.send(content=goodbye_message)
            else:
                await ctx.send(content=goodbye_message)

    @commands.command(name="autorole")
    @has_welcome_role()
    @commands.has_permissions(manage_roles=True)
    async def auto_role(self, ctx: commands.Context, role: discord.Role = None):
        """Set role yang akan di-assign otomatis ke member baru."""
        if role is None:
            # Show current auto-roles
            current_roles = self._get_auto_roles(ctx.guild)
            if current_roles:
                roles_text = ", ".join([r.mention for r in current_roles])
                embed = self._create_embed(
                    "🎭 Auto-Role",
                    f"Auto-role saat ini: {roles_text}",
                    config.COLORS["info"]
                )
            else:
                embed = self._create_embed(
                    "🎭 Auto-Role",
                    "Tidak ada auto-role yang diset.\nGunakan dashboard untuk mengatur.",
                    config.COLORS["info"]
                )
            return await ctx.send(embed=embed)

        # Check if bot can assign this role
        if role >= ctx.guild.me.top_role:
            embed = self._create_embed(
                "❌ Error",
                "Bot tidak bisa assign role yang lebih tinggi atau sama dengan role bot!",
                config.COLORS["error"]
            )
            return await ctx.send(embed=embed)

        self.auto_roles[ctx.guild.id] = role.id

        embed = self._create_embed(
            "✅ Auto-Role Set",
            f"Role {role.mention} akan diberikan ke member baru.",
            config.COLORS["success"]
        )
        await ctx.send(embed=embed)

    @commands.command(name="removeautorole")
    @has_welcome_role()
    @commands.has_permissions(manage_roles=True)
    async def remove_auto_role(self, ctx: commands.Context):
        """Hapus auto-role setting."""
        if ctx.guild.id in self.auto_roles:
            del self.auto_roles[ctx.guild.id]

        embed = self._create_embed(
            "✅ Auto-Role Removed",
            "Auto-role telah dihapus.",
            config.COLORS["success"]
        )
        await ctx.send(embed=embed)

    @commands.command(name="welcomeinfo")
    async def welcome_info(self, ctx: commands.Context):
        """Tampilkan info welcome settings."""
        settings = get_guild_settings(ctx.guild.id)

        info = "**Welcome Settings:**\n\n"
        if settings:
            info += f"📢 **Enable Welcome Image:** {settings.get('use_image', 0)}\n"
            info += f"🖼️ **Banner URL:** {settings.get('banner_url', 'Not set')}\n"
            info += f"📝 **Welcome Text:** {settings.get('welcome_text', 'WELCOME')}\n"
            info += f"📍 **Profile Position:** {settings.get('profile_position', 'center')}\n"
            info += f"🎨 **Text Color:** {settings.get('text_color', '#FFD700')}\n"
            info += f"🔤 **Font Family:** {settings.get('font_family', 'arial')}\n"
            info += f"↔️ **Banner Offset:** X={settings.get('banner_offset_x', 0)}, Y={settings.get('banner_offset_y', 0)}\n"
            info += f"👤 **Avatar Offset:** X={settings.get('avatar_offset_x', 0)}, Y={settings.get('avatar_offset_y', 0)}\n"
            info += f"📝 **Text Offset:** X={settings.get('text_offset_x', 0)}, Y={settings.get('text_offset_y', 0)}\n"
            info += f"✉️ **Welcome Template:** {settings.get('welcome_message', 'Not set')}\n"
        else:
            info += "No settings found in database!"

        # Goodbye Image Settings
        info += "\n\n**Goodbye Image Settings:**\n\n"
        if settings:
            info += f"📢 **Enable Goodbye Image (Separate):** {settings.get('use_goodbye_image', 0)}\n"
            info += f"🖼️ **Goodbye Banner URL:** {settings.get('goodbye_banner_url', 'Not set (uses welcome)')}\n"
            info += f"📝 **Goodbye Text:** {settings.get('goodbye_text', 'GOODBYE')}\n"
            info += f"📍 **Goodbye Profile Position:** {settings.get('goodbye_profile_position', 'center')}\n"
            info += f"🎨 **Goodbye Text Color:** {settings.get('goodbye_text_color', '#FF6B6B')}\n"
            info += f"🔤 **Goodbye Font Family:** {settings.get('goodbye_font_family', 'arial')}\n"
        else:
            info += "No settings found in database!"

        channel = self._get_welcome_channel(ctx.guild)
        roles = self._get_auto_roles(ctx.guild)

        info += f"\n\n📢 **Welcome Channel:** {channel.mention if channel else 'Not set'}\n"
        if roles:
            roles_text = ", ".join([r.mention for r in roles])
            info += f"🎭 **Auto-Role:** {roles_text}\n"
        else:
            info += "🎭 **Auto-Role:** Not set\n"
        info += f"👥 **Member Count:** {ctx.guild.member_count}"

        await ctx.send(info)

    # ==================== ERROR HANDLERS ====================
    @set_welcome.error
    @test_welcome.error
    @test_goodbye.error
    @auto_role.error
    @remove_auto_role.error
    async def welcome_error(self, ctx: commands.Context, error):
        """Handle welcome command errors."""
        if isinstance(error, commands.MissingPermissions):
            embed = self._create_embed(
                "❌ Permission Denied",
                "Kamu tidak memiliki permission untuk menggunakan command ini!",
                config.COLORS["error"]
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.ChannelNotFound):
            embed = self._create_embed(
                "❌ Channel Not Found",
                "Channel tidak ditemukan!",
                config.COLORS["error"]
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.RoleNotFound):
            embed = self._create_embed(
                "❌ Role Not Found",
                "Role tidak ditemukan!",
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
    await bot.add_cog(Welcome(bot))
