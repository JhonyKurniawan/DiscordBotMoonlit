"""
Music Cog
=========
Commands untuk memutar musik dari YouTube Music.
"""

import discord
from discord.ext import commands
from discord import ui
import asyncio
from typing import Optional, TYPE_CHECKING
import config
from utils.ytmusic_player import ytmusic_player, Song, FFMPEG_OPTIONS

# Check if database is available
try:
    from dashboard.backend import database as db
    HAS_DATABASE = True
except Exception as e:
    HAS_DATABASE = False
    print(f"❌ Music: Database import failed: {e}")

if TYPE_CHECKING:
    from discord import Interaction


class MusicControlView(ui.View):
    """Interactive buttons untuk music player."""

    def __init__(self, cog: 'Music', ctx: commands.Context, timeout: float = 600):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.ctx = ctx
        self.message: Optional[discord.Message] = None
        self.start_time: Optional[float] = None
        self.paused_duration: float = 0
        self.pause_start_time: Optional[float] = None

        # Update autoplay button based on current state
        self._update_autoplay_button()
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if user is in same voice channel."""
        if not interaction.user.voice:
            await interaction.response.send_message(
                "❌ Kamu harus join voice channel terlebih dahulu!",
                ephemeral=True
            )
            return False
        
        if interaction.guild.voice_client and interaction.user.voice.channel != interaction.guild.voice_client.channel:
            await interaction.response.send_message(
                "❌ Kamu harus berada di voice channel yang sama dengan bot!",
                ephemeral=True
            )
            return False
        
        return True

    def _update_autoplay_button(self):
        """Update autoplay button style and emoji based on current state."""
        try:
            is_autoplay = ytmusic_player.is_autoplay_active(self.ctx.guild.id)
            for item in self.children:
                if item.custom_id == "autoplay":
                    if is_autoplay:
                        item.style = discord.ButtonStyle.success
                        item.emoji = "✅"
                    else:
                        item.style = discord.ButtonStyle.secondary
                        item.emoji = "🎵"
                    break
        except Exception as e:
            print(f"Error updating autoplay button: {e}")

    async def on_timeout(self):
        """Disable all buttons on timeout."""
        for item in self.children:
            item.disabled = True

        if self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass

    def _calculate_total_duration(self, songs: list) -> str:
        """Calculate total duration dari list lagu. Returns formatted string."""
        total_seconds = 0
        for song in songs:
            if song.duration:
                try:
                    parts = song.duration.split(":")
                    if len(parts) == 2:  # MM:SS
                        total_seconds += int(parts[0]) * 60 + int(parts[1])
                    elif len(parts) == 3:  # HH:MM:SS
                        total_seconds += int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                except (ValueError, IndexError):
                    pass

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"

    def _get_queue_info(self) -> str:
        """Get current queue info for embed footer."""
        queue = ytmusic_player.get_queue(self.ctx.guild.id)
        volume = round(ytmusic_player.get_volume(self.ctx.guild.id) * 100)

        info = f"🔊 {volume}%"

        if len(queue.upcoming) > 0:
            total_duration = self._calculate_total_duration(queue.upcoming)
            info += f" | 📋 {len(queue.upcoming)} in queue ({total_duration})"

        if queue.loop_single:
            info += " | 🔂 Loop Current"
        elif queue.loop:
            info += " | 🔁 Loop All"

        return info

    def _create_progress_bar(self, current_seconds: int, total_seconds: int, length: int = 15) -> str:
        """Create a text-based progress bar."""
        if total_seconds <= 0:
            return "▬" * length
        
        progress = min(current_seconds / total_seconds, 1.0)
        filled = int(progress * length)
        
        bar = "▓" * filled + "░" * (length - filled)
        return bar

    def _format_time(self, seconds: int) -> str:
        """Format seconds to mm:ss."""
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins}:{secs:02d}"

    def _parse_duration(self, duration_str: str) -> int:
        """Parse duration string like '3:34' to seconds."""
        if not duration_str or duration_str == "Unknown":
            return 0
        
        try:
            parts = duration_str.split(":")
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except:
            pass
        return 0

    def _create_now_playing_embed(self, song: 'Song', elapsed_seconds: int = 0) -> discord.Embed:
        """Create now playing embed with progress bar."""
        # Check if unlimited play is active
        guild_id = self.ctx.guild.id
        if ytmusic_player.is_unlimited_play_active(guild_id):
            genre = ytmusic_player.get_unlimited_genre(guild_id)
            title = f"🎵 Now Playing (∞ {genre.title()})"
        else:
            title = "🎵 Now Playing"

        embed = discord.Embed(
            title=title,
            description=f"**[{song.title}]({song.youtube_url})**",
            color=config.COLORS["music"]
        )

        embed.add_field(name="Artist", value=song.artist, inline=True)
        embed.add_field(name="Duration", value=song.duration or "Unknown", inline=True)

        if song.requester:
            embed.add_field(name="Requested by", value=song.requester.mention, inline=True)

        if song.thumbnail:
            embed.set_thumbnail(url=song.thumbnail)

        # Add progress bar if duration is known
        duration_seconds = self._parse_duration(song.duration or "0")
        if duration_seconds > 0:
            progress_bar = self._create_progress_bar(elapsed_seconds, duration_seconds)
            embed.add_field(
                name="Progress",
                value=f"`{self._format_time(elapsed_seconds)}` / `{self._format_time(duration_seconds)}`\n{progress_bar}",
                inline=False
            )

        # Footer with volume and queue info
        embed.set_footer(text=self._get_queue_info())

        return embed


    async def update_embed(self):
        """Update the now playing embed with current info."""
        if not self.message:
            return

        song = ytmusic_player.now_playing.get(self.ctx.guild.id)
        if not song:
            return

        try:
            # Get elapsed time (we'll estimate based on when song started)
            elapsed = getattr(self, '_elapsed_seconds', 0)
            embed = self._create_now_playing_embed(song, elapsed)

            # Update autoplay button state
            self._update_autoplay_button()

            await self.message.edit(embed=embed, view=self)
        except Exception as e:
            print(f"Error updating embed: {e}")

    # ==================== ROW 0: Main Controls ====================
    @ui.button(label="Prev", emoji="⏮️", style=discord.ButtonStyle.secondary, custom_id="prev", row=0)
    async def previous_button(self, interaction: discord.Interaction, button: ui.Button):
        """Previous song button."""
        queue = ytmusic_player.get_queue(self.ctx.guild.id)

        if queue.current_index > 0:
            queue.current_index -= 2  # -2 because _play_next will +1
            if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
                ytmusic_player.set_transitioning(interaction.guild.id, True)
                interaction.guild.voice_client.stop()
            await interaction.response.send_message("⏮️ Playing previous song...", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Tidak ada lagu sebelumnya!", ephemeral=True)

    @ui.button(label="Pause", emoji="⏸️", style=discord.ButtonStyle.primary, custom_id="pause_resume", row=0)
    async def pause_resume_button(self, interaction: discord.Interaction, button: ui.Button):
        """Pause/Resume button."""
        vc = interaction.guild.voice_client
        import time

        if not vc:
            await interaction.response.send_message("❌ Bot tidak ada di voice channel!", ephemeral=True)
            return

        # Check if we're in a transitioning state (song being skipped/changed)
        if ytmusic_player.is_transitioning(interaction.guild.id):
            await interaction.response.send_message("⏳ Please wait...", ephemeral=True)
            return

        if vc.is_playing():
            vc.pause()
            button.label = "Play"
            button.emoji = "▶️"
            button.style = discord.ButtonStyle.success
            # Track pause start time
            self.pause_start_time = time.time()
            await interaction.response.edit_message(view=self)
        elif vc.is_paused():
            vc.resume()
            button.label = "Pause"
            button.emoji = "⏸️"
            button.style = discord.ButtonStyle.primary
            # Calculate pause duration and add to total
            if self.pause_start_time:
                pause_duration = time.time() - self.pause_start_time
                self.paused_duration += pause_duration
                self.pause_start_time = None
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.send_message("❌ Tidak ada musik yang diputar!", ephemeral=True)

    @ui.button(label="Skip", emoji="⏭️", style=discord.ButtonStyle.secondary, custom_id="next", row=0)
    async def next_button(self, interaction: discord.Interaction, button: ui.Button):
        """Skip to next song."""
        vc = interaction.guild.voice_client

        if vc and (vc.is_playing() or vc.is_paused()):
            # Set transitioning state to prevent race conditions
            ytmusic_player.set_transitioning(interaction.guild.id, True)
            vc.stop()  # This triggers _play_next
            await interaction.response.send_message("⏭️ Skipped!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Tidak ada musik yang diputar!", ephemeral=True)

    @ui.button(label="Stop", emoji="⏹️", style=discord.ButtonStyle.danger, custom_id="stop", row=0)
    async def stop_button(self, interaction: discord.Interaction, button: ui.Button):
        """Stop and disconnect."""
        vc = interaction.guild.voice_client

        if vc:
            ytmusic_player.cleanup(self.ctx.guild.id)
            await vc.disconnect()

            # Disable all buttons
            for item in self.children:
                item.disabled = True

            await interaction.response.edit_message(
                embed=discord.Embed(
                    title="⏹️ Stopped",
                    description="Bot telah disconnect dan queue dikosongkan.",
                    color=config.COLORS["info"]
                ),
                view=self
            )

            # Clean up references but don't delete the message (user can see it stopped)
            if self.ctx.guild.id in self.cog.now_playing_views:
                del self.cog.now_playing_views[self.ctx.guild.id]
            if self.ctx.guild.id in self.cog.song_start_times:
                del self.cog.song_start_times[self.ctx.guild.id]
            self.cog._cancel_progress_task(self.ctx.guild.id)
        else:
            await interaction.response.send_message("❌ Bot tidak ada di voice channel!", ephemeral=True)


    @ui.button(label="Loop", emoji="🔁", style=discord.ButtonStyle.secondary, custom_id="loop", row=0)
    async def loop_button(self, interaction: discord.Interaction, button: ui.Button):
        """Toggle loop mode."""
        queue = ytmusic_player.get_queue(self.ctx.guild.id)
        
        # Cycle through modes: off -> single -> all -> off
        if not queue.loop and not queue.loop_single:
            queue.loop_single = True
            button.emoji = "🔂"
            button.label = "Current"
            status = "Loop Current Music 🔂"
        elif queue.loop_single:
            queue.loop_single = False
            queue.loop = True
            button.emoji = "🔁"
            button.label = "All"
            status = "Loop All Queue 🔁"
        else:
            queue.loop = False
            button.emoji = "🔁"
            button.label = "Loop"
            status = "Loop Off"
        
        # Update embed with new footer
        await self.update_embed()
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f"🔁 {status}", ephemeral=True)


    # ==================== ROW 1: Additional Controls ====================
    @ui.button(label="Shuffle", emoji="🔀", style=discord.ButtonStyle.secondary, custom_id="shuffle", row=1)
    async def shuffle_button(self, interaction: discord.Interaction, button: ui.Button):
        """Shuffle queue."""
        queue = ytmusic_player.get_queue(self.ctx.guild.id)
        
        if len(queue) < 2:
            await interaction.response.send_message("❌ Tidak cukup lagu untuk shuffle!", ephemeral=True)
            return
        
        queue.shuffle()
        await interaction.response.send_message("🔀 Queue telah diacak!", ephemeral=True)

    @ui.button(label="Queue", emoji="📋", style=discord.ButtonStyle.secondary, custom_id="queue", row=1)
    async def queue_button(self, interaction: discord.Interaction, _button: ui.Button):
        """Show queue with pagination."""
        queue = ytmusic_player.get_queue(self.ctx.guild.id)

        if not queue.songs:
            await interaction.response.send_message("📋 Queue kosong!", ephemeral=True)
            return

        # Create pagination view
        view = QueuePaginationView(self.ctx.guild.id, page=0)
        await interaction.response.send_message(embed=view.get_embed(), view=view, ephemeral=True)

    @ui.button(label="Vol -", emoji="🔉", style=discord.ButtonStyle.secondary, custom_id="vol_down", row=1)
    async def volume_down_button(self, interaction: discord.Interaction, button: ui.Button):
        """Decrease volume by 10%."""
        # Use integer math to avoid floating point issues
        current_vol_percent = round(ytmusic_player.get_volume(self.ctx.guild.id) * 100)
        new_vol_percent = max(0, current_vol_percent - 10)
        new_vol = new_vol_percent / 100

        ytmusic_player.set_volume(self.ctx.guild.id, new_vol)

        # Save to database
        if HAS_DATABASE:
            try:
                db.update_guild_settings(self.ctx.guild.id, {'music_default_volume': new_vol_percent})
            except Exception as e:
                print(f"Error saving volume to DB: {e}")

        vc = interaction.guild.voice_client
        if vc and vc.source:
            vc.source.volume = new_vol

        # Update embed with new volume in footer
        await self.update_embed()
        await interaction.response.send_message(
            f"🔉 Volume: {new_vol_percent}%",
            ephemeral=True
        )

    @ui.button(label="Vol +", emoji="🔊", style=discord.ButtonStyle.secondary, custom_id="vol_up", row=1)
    async def volume_up_button(self, interaction: discord.Interaction, button: ui.Button):
        """Increase volume by 10%."""
        # Use integer math to avoid floating point issues
        current_vol_percent = round(ytmusic_player.get_volume(self.ctx.guild.id) * 100)
        new_vol_percent = min(100, current_vol_percent + 10)
        new_vol = new_vol_percent / 100

        ytmusic_player.set_volume(self.ctx.guild.id, new_vol)

        # Save to database
        if HAS_DATABASE:
            try:
                db.update_guild_settings(self.ctx.guild.id, {'music_default_volume': new_vol_percent})
            except Exception as e:
                print(f"Error saving volume to DB: {e}")

        vc = interaction.guild.voice_client
        if vc and vc.source:
            vc.source.volume = new_vol

        # Update embed with new volume in footer
        await self.update_embed()
        await interaction.response.send_message(
            f"🔊 Volume: {new_vol_percent}%",
            ephemeral=True
        )

    @ui.button(label="Autoplay", emoji="🎵", style=discord.ButtonStyle.secondary, custom_id="autoplay", row=1)
    async def autoplay_button(self, interaction: discord.Interaction, button: ui.Button):
        """Toggle autoplay mode."""
        is_active = ytmusic_player.toggle_autoplay(self.ctx.guild.id)

        # Update button appearance
        if is_active:
            button.style = discord.ButtonStyle.success
            button.emoji = "✅"
            await interaction.response.send_message("🎵 Autoplay diaktifkan! Lagu serupa akan otomatis ditambahkan.", ephemeral=True)
        else:
            button.style = discord.ButtonStyle.secondary
            button.emoji = "🎵"
            await interaction.response.send_message("🎵 Autoplay dinonaktifkan.", ephemeral=True)

        # Update the embed to show autoplay status
        await self.update_embed()

    @ui.button(label="Clear", emoji="🗑️", style=discord.ButtonStyle.danger, custom_id="clear", row=2)
    async def clear_queue_button(self, interaction: discord.Interaction, button: ui.Button):
        """Remove the last song from the queue."""
        queue = ytmusic_player.get_queue(self.ctx.guild.id)

        if len(queue.songs) <= 1:  # Only current song or empty
            await interaction.response.send_message("❌ Tidak ada lagu dalam queue untuk dihapus!", ephemeral=True)
            return

        # Remove the last song (most recently added)
        removed_song = queue.songs.pop()
        await interaction.response.send_message(f"🗑️ Menghapus lagu terakhir: **{removed_song.title}**", ephemeral=True)

    @ui.button(label="Lyrics", emoji="📜", style=discord.ButtonStyle.success, custom_id="lyrics", row=2)
    async def lyrics_button(self, interaction: discord.Interaction, button: ui.Button):
        """Show lyrics for current song."""
        song = ytmusic_player.now_playing.get(self.ctx.guild.id)

        if not song:
            await interaction.response.send_message("❌ Tidak ada lagu yang sedang diputar!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Fetch lyrics with title and artist for better search
        lyrics = await self._fetch_lyrics(song.video_id, song.title, song.artist)

        if lyrics:
            # Truncate if too long for Discord message (4096 char limit)
            if len(lyrics) > 3800:
                lyrics = lyrics[:3800] + "\n\n... (lyrics terpotong karena terlalu panjang)"

            # Split into chunks if needed
            chunks = []
            current_chunk = ""
            for line in lyrics.split('\n'):
                if len(current_chunk) + len(line) + 1 > 1900:  # Leave room for more content
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = line
                else:
                    current_chunk = current_chunk + "\n" + line if current_chunk else line

            if current_chunk:
                chunks.append(current_chunk)

            # Send lyrics
            for i, chunk in enumerate(chunks):
                title = f"📜 Lyrics - {song.title}" if i == 0 else "📜 Lyrics (continued)"
                embed = discord.Embed(
                    title=title,
                    description=f"```\n{chunk}\n```",
                    color=config.COLORS["music"]
                )
                if i == 0 and song.thumbnail:
                    embed.set_thumbnail(url=song.thumbnail)
                embed.set_footer(text=f"{song.artist} | {song.duration or 'Unknown'}")

                try:
                    await interaction.followup.send(embed=embed, ephemeral=True)
                except:
                    # If too many followups, try regular message
                    await interaction.channel.send(embed=embed)
        else:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Tidak Ada Lyrics",
                    description="Lyrics tidak tersedia untuk lagu ini",
                    color=config.COLORS["error"]
                ),
                ephemeral=True
            )

    async def _fetch_lyrics(self, video_id: str, title: str = None, artist: str = None) -> Optional[str]:
        """Fetch lyrics from multiple sources."""
        import aiohttp
        from urllib.parse import quote

        try:
            # Method 1: Try lyrics.ovh with video_id (YouTube ID format)
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://lyrics.ovh/v1/{video_id}",
                    headers={"User-Agent": "Mozilla/5.0"}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("lyrics"):
                            lyrics = data["lyrics"]
                            lyrics = lyrics.replace("\\n", "\n")
                            return lyrics

            # Method 2: Try with artist and title (properly URL encoded)
            if artist and title:
                # Clean and encode artist and title
                artist_clean = quote(artist.lower().strip())
                title_clean = quote(title.lower().strip())

                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"https://lyrics.ovh/v1/{artist_clean}/{title_clean}",
                        headers={"User-Agent": "Mozilla/5.0"}
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("lyrics"):
                                lyrics = data["lyrics"]
                                lyrics = lyrics.replace("\\n", "\n")
                                return lyrics

            # Method 3: Try with just artist/title formatted differently
            if artist and title:
                # Remove special characters and use simpler format
                artist_simple = ''.join(c for c in artist if c.isalnum() or c.isspace()).strip().lower().replace(' ', '')
                title_simple = ''.join(c for c in title if c.isalnum() or c.isspace()).strip().lower().replace(' ', '')

                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"https://lyrics.ovh/v1/{artist_simple}/{title_simple}",
                        headers={"User-Agent": "Mozilla/5.0"}
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("lyrics"):
                                lyrics = data["lyrics"]
                                lyrics = lyrics.replace("\\n", "\n")
                                return lyrics

            # Method 4: Try LRCLIB API (another free lyrics API)
            if artist and title:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://lrclib.net/api/get",
                        params={"artist_name": artist, "track_name": title},
                        headers={"User-Agent": "Mozilla/5.0"}
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if isinstance(data, list) and data:
                                # Get first result
                                result = data[0]
                                if result.get("lyrics"):
                                    return result["lyrics"]
                            elif isinstance(data, dict) and data.get("lyrics"):
                                return data["lyrics"]

        except Exception as e:
            print(f"Error fetching lyrics: {e}")

        return None

    @staticmethod
    async def _fetch_lyrics_static(video_id: str, title: str = None, artist: str = None) -> Optional[str]:
        """Static method to fetch lyrics - can be called without instance."""
        import aiohttp
        from urllib.parse import quote

        try:
            # Method 1: Try lyrics.ovh with video_id
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://lyrics.ovh/v1/{video_id}",
                    headers={"User-Agent": "Mozilla/5.0"}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("lyrics"):
                            lyrics = data["lyrics"]
                            lyrics = lyrics.replace("\\n", "\n")
                            return lyrics

            # Method 2: Try with artist and title (URL encoded)
            if artist and title:
                artist_clean = quote(artist.lower().strip())
                title_clean = quote(title.lower().strip())

                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"https://lyrics.ovh/v1/{artist_clean}/{title_clean}",
                        headers={"User-Agent": "Mozilla/5.0"}
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("lyrics"):
                                lyrics = data["lyrics"]
                                lyrics = lyrics.replace("\\n", "\n")
                                return lyrics

            # Method 3: Try simplified format (no special characters)
            if artist and title:
                artist_simple = ''.join(c for c in artist if c.isalnum() or c.isspace()).strip().lower().replace(' ', '')
                title_simple = ''.join(c for c in title if c.isalnum() or c.isspace()).strip().lower().replace(' ', '')

                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"https://lyrics.ovh/v1/{artist_simple}/{title_simple}",
                        headers={"User-Agent": "Mozilla/5.0"}
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("lyrics"):
                                lyrics = data["lyrics"]
                                lyrics = lyrics.replace("\\n", "\n")
                                return lyrics

            # Method 4: Try LRCLIB API
            if artist and title:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://lrclib.net/api/get",
                        params={"artist_name": artist, "track_name": title},
                        headers={"User-Agent": "Mozilla/5.0"}
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if isinstance(data, list) and data:
                                result = data[0]
                                if result.get("lyrics"):
                                    return result["lyrics"]
                            elif isinstance(data, dict) and data.get("lyrics"):
                                return data["lyrics"]

        except Exception as e:
            print(f"Error fetching lyrics: {e}")

        return None


class QueuePaginationView(ui.View):
    """Pagination view untuk music queue."""

    def __init__(self, guild_id: int, page: int = 0, page_size: int = 10):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self.page = page
        self.page_size = page_size
        self.update_queue()

    def update_queue(self):
        """Update queue info dan hitung total pages."""
        self.queue = ytmusic_player.get_queue(self.guild_id)
        upcoming_count = len(self.queue.upcoming)
        self.total_pages = max(1, (upcoming_count + self.page_size - 1) // self.page_size)
        self.update_buttons()

    def update_buttons(self):
        """Enable/disable buttons berdasarkan current page."""
        for child in self.children:
            if isinstance(child, ui.Button):
                child.disabled = False

        # Disable First/Previous di first page
        if self.page <= 0:
            self.first_page_button.disabled = True
            self.previous_page_button.disabled = True

        # Disable Next/Last di last page
        if self.page >= self.total_pages - 1:
            self.next_page_button.disabled = True
            self.last_page_button.disabled = True

    def get_embed(self) -> discord.Embed:
        """Generate embed untuk current page."""
        if not self.queue.songs:
            return discord.Embed(
                title="📋 Queue",
                description="Queue kosong!",
                color=config.COLORS["music"]
            )

        description = ""

        # Current song
        current = self.queue.current_song
        if current:
            duration_str = f" [{current.duration}]" if current.duration else ""
            requester_str = f" | Requested by {current.requester.display_name}" if current.requester else ""
            description += f"**Now Playing:**\n🎵 {current.title} - {current.artist}{duration_str}{requester_str}\n\n"

        # Upcoming songs
        upcoming = self.queue.upcoming
        if upcoming:
            start_idx = self.page * self.page_size
            end_idx = start_idx + self.page_size
            page_songs = upcoming[start_idx:end_idx]

            description += f"**Up Next (Page {self.page + 1}/{self.total_pages}):**\n"
            for i, song in enumerate(page_songs, start_idx + 1):
                duration_str = f" [{song.duration}]" if song.duration else ""
                requester_str = f" | {song.requester.display_name}" if song.requester else ""
                description += f"`{i}.` {song.title} - {song.artist}{duration_str}{requester_str}\n"
        else:
            description += "*Tidak ada lagu dalam antrian*"

        embed = discord.Embed(
            title=f"📋 Queue ({len(self.queue)} songs)",
            description=description,
            color=config.COLORS["music"]
        )

        # Add loop status field
        loop_status = "Off"
        if self.queue.loop_single:
            loop_status = "Single 🔂"
        elif self.queue.loop:
            loop_status = "All 🔁"
        embed.add_field(name="Loop", value=loop_status, inline=True)

        # Add volume field
        volume = int(ytmusic_player.get_volume(self.guild_id) * 100)
        embed.add_field(name="Volume", value=f"{volume}%", inline=True)

        # Add footer dengan page info dan total duration
        upcoming_count = len(self.queue.upcoming)
        if upcoming_count > 0:
            total_duration = self._calculate_total_duration(upcoming)
            embed.set_footer(text=f"⏹️ Page {self.page + 1}/{self.total_pages} | {upcoming_count} in queue ({total_duration})")
        else:
            embed.set_footer(text=f"⏹️ Page {self.page + 1}/{self.total_pages}")

        return embed

    def _calculate_total_duration(self, songs: list) -> str:
        """Calculate total duration dari list lagu. Returns formatted string."""
        total_seconds = 0
        for song in songs:
            if song.duration:
                try:
                    parts = song.duration.split(":")
                    if len(parts) == 2:  # MM:SS
                        total_seconds += int(parts[0]) * 60 + int(parts[1])
                    elif len(parts) == 3:  # HH:MM:SS
                        total_seconds += int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                except (ValueError, IndexError):
                    pass

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"

    @ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary, row=0)
    async def first_page_button(self, interaction: discord.Interaction, _button: ui.Button):
        """Go to first page."""
        self.page = 0
        self.update_queue()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @ui.button(emoji="◀️", style=discord.ButtonStyle.secondary, row=0)
    async def previous_page_button(self, interaction: discord.Interaction, _button: ui.Button):
        """Go to previous page."""
        if self.page > 0:
            self.page -= 1
            self.update_queue()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @ui.button(emoji="▶️", style=discord.ButtonStyle.secondary, row=0)
    async def next_page_button(self, interaction: discord.Interaction, _button: ui.Button):
        """Go to next page."""
        if self.page < self.total_pages - 1:
            self.page += 1
            self.update_queue()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, row=0)
    async def last_page_button(self, interaction: discord.Interaction, _button: ui.Button):
        """Go to last page."""
        self.page = max(0, self.total_pages - 1)
        self.update_queue()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)


class Music(commands.Cog):
    """Cog untuk music player commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Store now playing message and view per guild
        self.now_playing_messages: dict[int, discord.Message] = {}
        self.now_playing_views: dict[int, MusicControlView] = {}
        # Track song start times for progress bar
        self.song_start_times: dict[int, float] = {}
        # Track progress update tasks
        self.progress_tasks: dict[int, asyncio.Task] = {}

    def _create_embed(self, title: str, description: str, color: int) -> discord.Embed:
        """Helper untuk membuat embed."""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        return embed

    async def _send_with_auto_delete(self, ctx: commands.Context, embed: discord.Embed,
                                     view: discord.ui.View = None, delay: int = 10) -> discord.Message:
        """Send a message and auto-delete it if the setting is enabled.

        Args:
            ctx: Command context
            embed: Embed to send
            view: Optional view to attach
            delay: Delay before deletion in seconds (default 10)

        Returns:
            The sent message
        """
        # Check if auto-delete is enabled
        auto_delete = False
        if HAS_DATABASE:
            try:
                settings = db.get_guild_settings(ctx.guild.id)
                if settings and settings.get('auto_delete_messages'):
                    auto_delete = settings['auto_delete_messages'] == 1
            except Exception as e:
                print(f"Error checking auto_delete setting: {e}")

        # Send message
        if view:
            message = await ctx.send(embed=embed, view=view)
        else:
            message = await ctx.send(embed=embed)

        # Schedule deletion if enabled
        if auto_delete:
            asyncio.create_task(self._delete_after(message, delay))

        return message

    async def _delete_after(self, message: discord.Message, delay: int):
        """Delete a message after a delay."""
        await asyncio.sleep(delay)
        try:
            await message.delete()
        except:
            pass  # Message already deleted or no permission

    def _create_now_playing_embed(self, song: Song, guild_id: int = None) -> discord.Embed:
        """Buat embed untuk now playing."""
        # Check if unlimited play or autoplay is active
        if guild_id:
            if ytmusic_player.is_unlimited_play_active(guild_id):
                genre = ytmusic_player.get_unlimited_genre(guild_id)
                title = f"🎵 Now Playing (∞ {genre.title()})"
            elif ytmusic_player.is_autoplay_active(guild_id):
                title = "🎵 Now Playing (🎵 Autoplay On)"
            else:
                title = "🎵 Now Playing"
        else:
            title = "🎵 Now Playing"

        embed = discord.Embed(
            title=title,
            description=f"**[{song.title}]({song.youtube_url})**",
            color=config.COLORS["music"]
        )
        embed.add_field(name="Artist", value=song.artist, inline=True)
        embed.add_field(name="Duration", value=song.duration or "Unknown", inline=True)

        if song.requester:
            embed.add_field(name="Requested by", value=song.requester.mention, inline=True)

        if song.thumbnail:
            embed.set_thumbnail(url=song.thumbnail)

        return embed

    async def _ensure_voice(self, ctx: commands.Context) -> bool:
        """Pastikan user ada di voice channel."""
        if not ctx.author.voice:
            embed = self._create_embed(
                "❌ Error",
                "Kamu harus join voice channel terlebih dahulu!",
                config.COLORS["error"]
            )
            await ctx.send(embed=embed)
            return False
        return True

    async def _check_music_channel(self, ctx: commands.Context) -> bool:
        """Check if music commands are allowed in this channel."""
        if HAS_DATABASE:
            from dashboard.backend import database as db
            settings = db.get_guild_settings(ctx.guild.id)
            if settings:
                music_channel_id = settings.get('music_channel_id')
                if music_channel_id:
                    # Only check if the channel still exists
                    channel = ctx.guild.get_channel(music_channel_id)
                    if channel and ctx.channel.id != music_channel_id:
                        embed = self._create_embed(
                            "❌ Wrong Channel",
                            f"Music commands only work in <#{channel.name}>!",
                            config.COLORS["error"]
                        )
                        await ctx.send(embed=embed)
                        return False
        return True

    async def _connect_voice(self, ctx: commands.Context) -> Optional[discord.VoiceClient]:
        """Connect ke voice channel user."""
        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                # Check if bot is currently playing music
                is_active = ctx.voice_client.is_playing() or ctx.voice_client.is_paused()

                if is_active:
                    # Bot is playing/paused - don't move
                    embed = self._create_embed(
                        "⚠️ Bot Sedang Digunakan",
                        f"Bot sedang memutar musik di **{ctx.voice_client.channel.name}**!\n\n"
                        f"Join ke channel tersebut untuk menggunakan bot, atau tunggu sampai musik selesai.",
                        config.COLORS["warning"]
                    )
                    await ctx.send(embed=embed)
                    return None

                # Check if there are other users (non-bots) in the current channel
                current_channel = ctx.voice_client.channel
                other_users = [m for m in current_channel.members if not m.bot]

                if other_users:
                    # Don't move, show warning
                    embed = self._create_embed(
                        "⚠️ Bot Sedang Digunakan",
                        f"Bot sedang digunakan di **{current_channel.name}** oleh {len(other_users)} user lain.\n"
                        f"Users: {', '.join([u.mention for u in other_users[:3]])}"
                        + (f" dan {len(other_users) - 3} lainnya" if len(other_users) > 3 else ""),
                        config.COLORS["warning"]
                    )
                    embed.add_field(
                        name="💡 Solusi",
                        value="Tunggu sampai mereka selesai, atau minta mereka untuk stop musik terlebih dahulu.",
                        inline=False
                    )
                    await ctx.send(embed=embed)
                    return None
                else:
                    # No other users and not playing, safe to move
                    await ctx.voice_client.move_to(ctx.author.voice.channel)
            return ctx.voice_client
        else:
            return await ctx.author.voice.channel.connect()

    async def _maybe_delete_user_message(self, ctx: commands.Context):
        """Delete user's command message if auto-delete is enabled."""
        if not HAS_DATABASE:
            print("[AUTO-DELETE] Database not available")
            return

        try:
            from dashboard.backend import database as db
            settings = db.get_guild_settings(ctx.guild.id)
            auto_delete = settings.get('auto_delete', 0) if settings else 0
            print(f"[AUTO-DELETE] Guild {ctx.guild.id}: auto_delete={auto_delete}")
            if auto_delete:
                try:
                    await ctx.message.delete()
                    print(f"[AUTO-DELETE] Deleted message from {ctx.author}")
                except discord.NotFound:
                    print("[AUTO-DELETE] Message already deleted")
                    pass  # Message already deleted
                except Exception as e:
                    print(f"[AUTO-DELETE] Error deleting: {e}")
            else:
                print("[AUTO-DELETE] Feature disabled for this guild")
        except Exception as e:
            print(f"[AUTO-DELETE] Error checking setting: {e}")

    async def _has_messages_after(self, message: discord.Message) -> bool:
        """Check if there are user messages after the given message."""
        try:
            async for msg in message.channel.history(after=message, limit=10):
                # Ignore bot messages and the music message itself
                if not msg.author.bot and msg.id != message.id:
                    return True
            return False
        except Exception as e:
            print(f"Error checking messages: {e}")
            return True  # Default to new message on error

    async def _update_progress(self, guild_id: int, view: MusicControlView, duration_seconds: int):
        """Background task to update progress bar."""
        import time

        message = self.now_playing_messages.get(guild_id)
        if not message or not view:
            return

        start_time = view.start_time or 0
        interval = getattr(config, 'PROGRESS_UPDATE_INTERVAL', 1)

        while True:
            await asyncio.sleep(interval)

            # Check if still connected
            vc = self.bot.get_guild(guild_id).voice_client
            if not vc:
                break

            # Check if song changed or stopped (not paused)
            current_song = ytmusic_player.now_playing.get(guild_id)
            if not current_song:
                break

            # If completely stopped (not playing AND not paused), exit
            if not vc.is_playing() and not vc.is_paused():
                break

            # Calculate elapsed time
            current_time = time.time()
            elapsed = int((current_time - start_time) - view.paused_duration)

            # If currently paused, don't count the pause time
            if vc.is_paused() and view.pause_start_time:
                # Subtract the current pause duration from elapsed
                current_pause_duration = current_time - view.pause_start_time
                elapsed = int(elapsed - current_pause_duration)

            elapsed = max(0, elapsed)

            # Update if still under duration
            if elapsed <= duration_seconds:
                try:
                    embed = view._create_now_playing_embed(current_song, elapsed)
                    await message.edit(embed=embed)
                except discord.NotFound:
                    break
                except Exception as e:
                    print(f"Error updating progress: {e}")
                    break
            else:
                break

    def _cancel_progress_task(self, guild_id: int):
        """Cancel progress update task for a guild."""
        if guild_id in self.progress_tasks:
            task = self.progress_tasks[guild_id]
            if not task.done():
                task.cancel()
            del self.progress_tasks[guild_id]

    async def _cleanup_old_messages(self, guild_id: int):
        """Clean up old now playing messages for a guild."""
        print(f"[CLEANUP] Starting cleanup for guild {guild_id}")

        # Clean up old message
        if guild_id in self.now_playing_messages:
            old_message = self.now_playing_messages[guild_id]
            print(f"[CLEANUP] Found old message to delete: {old_message.id}")
            try:
                # Try to delete the message
                await old_message.delete()
                print(f"[CLEANUP] Successfully deleted old message")
            except discord.NotFound:
                print(f"[CLEANUP] Message already deleted (NotFound)")
                pass  # Message already deleted
            except discord.HTTPException as e:
                print(f"[CLEANUP] HTTP error deleting old message: {e}")
            except Exception as e:
                print(f"[CLEANUP] Error deleting old message: {e}")
            finally:
                # Always remove from dictionary
                del self.now_playing_messages[guild_id]
        else:
            print(f"[CLEANUP] No old message found in dictionary for guild {guild_id}")

        # Clean up old view reference
        if guild_id in self.now_playing_views:
            del self.now_playing_views[guild_id]

        # Clean up song start times
        if guild_id in self.song_start_times:
            del self.song_start_times[guild_id]

        # Cancel any running progress task
        self._cancel_progress_task(guild_id)

        print(f"[CLEANUP] Cleanup completed for guild {guild_id}")

    def _play_next(self, ctx: commands.Context, error=None):
        """Callback untuk play next song."""
        if error:
            print(f"Player error: {error}")

        queue = ytmusic_player.get_queue(ctx.guild.id)
        next_song = queue.next()

        if next_song and ctx.voice_client:
            # User song in queue - play it (priority over buffer)
            asyncio.run_coroutine_threadsafe(
                self._play_song(ctx, next_song),
                self.bot.loop
            )
        else:
            # Queue empty - check buffer first
            buffer = ytmusic_player.get_buffer(ctx.guild.id)
            if buffer and ctx.voice_client:
                # Play buffered song
                ytmusic_player.clear_buffer(ctx.guild.id)
                print(f"[BUFFER] Playing buffered song: {buffer.title}")
                asyncio.run_coroutine_threadsafe(
                    self._play_song(ctx, buffer),
                    self.bot.loop
                )
            elif ytmusic_player.is_autoplay_active(ctx.guild.id):
                # Autoplay is on - fetch similar song
                asyncio.run_coroutine_threadsafe(
                    self._play_autoplay_song(ctx),
                    self.bot.loop
                )
            elif ytmusic_player.is_unlimited_play_active(ctx.guild.id):
                # No buffer, fetch immediately (fallback)
                genre = ytmusic_player.get_unlimited_genre(ctx.guild.id)
                asyncio.run_coroutine_threadsafe(
                    self._play_unlimited_song(ctx, genre),
                    self.bot.loop
                )
            else:
                # No unlimited play, schedule disconnect after timeout
                asyncio.run_coroutine_threadsafe(
                    self._auto_disconnect(ctx),
                    self.bot.loop
                )

    async def _play_unlimited_song(self, ctx: commands.Context, genre: str):
        """Fetch and play a random song for unlimited play."""
        # Get 1 random song from genre
        songs = await ytmusic_player.get_random_songs_by_genre(
            genre,
            count=1,
            requester=ctx.guild.me  # Bot as requester
        )

        if not songs:
            # No songs found, disable unlimited play
            ytmusic_player.clear_unlimited_play(ctx.guild.id)
            print(f"[UPLAY] No songs found for genre: {genre}")
            return

        song = songs[0]

        # Verify stream URL is available before playing
        stream_url = await ytmusic_player.get_stream_url(song.video_id)
        if not stream_url:
            # Stream URL not available, try to get another song
            print(f"[UPLAY] Stream URL not available for {song.title}, trying another...")
            # Recursively try to get another song
            await self._play_unlimited_song(ctx, genre)
            return

        # Add to queue
        queue = ytmusic_player.get_queue(ctx.guild.id)
        queue.add(song)

        # Play the song
        await self._play_song(ctx, song)
        print(f"[UPLAY] Now playing (unlimited {genre}): {song.title} - {song.artist}")

    async def _play_autoplay_song(self, ctx: commands.Context):
        """Fetch and play a similar song for autoplay."""
        current_song = ytmusic_player.now_playing.get(ctx.guild.id)

        if not current_song:
            print("[AUTOPLAY] No current song, disabling autoplay")
            ytmusic_player.set_autoplay(ctx.guild.id, False)
            return

        print(f"[AUTOPLAY] Finding similar songs to: {current_song.title} - {current_song.artist}")

        # Get similar songs based on current song
        songs = await ytmusic_player.get_similar_songs(current_song, count=1)

        if not songs:
            print(f"[AUTOPLAY] No similar songs found, trying fallback to popular songs...")
            # Fallback: try to get a popular song from a default genre
            songs = await ytmusic_player.get_random_songs_by_genre(
                "pop",  # Use pop as fallback genre
                count=1,
                requester=ctx.guild.me
            )

            if not songs:
                print(f"[AUTOPLAY] Fallback also failed, disabling autoplay")
                ytmusic_player.set_autoplay(ctx.guild.id, False)
                return

            print(f"[AUTOPLAY] Using fallback pop song: {songs[0].title}")

        song = songs[0]

        # Verify stream URL is available before playing
        stream_url = await ytmusic_player.get_stream_url(song.video_id)
        if not stream_url:
            print(f"[AUTOPLAY] Stream URL not available for {song.title}, trying another...")
            await self._play_autoplay_song(ctx)
            return

        # Add to queue
        queue = ytmusic_player.get_queue(ctx.guild.id)
        queue.add(song)

        # Play the song
        await self._play_song(ctx, song)
        print(f"[AUTOPLAY] Now playing (autoplay similar): {song.title} - {song.artist}")

    async def _preload_next_song(self, ctx: commands.Context):
        """Preload next song for unlimited play (runs in background)."""
        genre = ytmusic_player.get_unlimited_genre(ctx.guild.id)

        # Try to get a valid song with working stream URL
        max_retries = 3
        for attempt in range(max_retries):
            songs = await ytmusic_player.get_random_songs_by_genre(
                genre,
                count=1,
                requester=ctx.guild.me
            )

            if not songs:
                continue

            song = songs[0]

            # Verify stream URL is available
            stream_url = await ytmusic_player.get_stream_url(song.video_id)
            if stream_url:
                # Valid song - add to buffer
                ytmusic_player.set_buffer(ctx.guild.id, song)
                print(f"[BUFFER] Preloaded: {song.title} - {song.artist} ({genre})")
                return
            else:
                print(f"[BUFFER] Skipping {song.title} - no stream URL available")

        print(f"[BUFFER] Failed to preload after {max_retries} attempts")

    async def _preload_similar_song(self, ctx: commands.Context):
        """Preload a similar song for autoplay mode (runs in background)."""
        current_song = ytmusic_player.now_playing.get(ctx.guild.id)

        if not current_song:
            print("[AUTOPLAY BUFFER] No current song to base similarity on")
            return

        print(f"[AUTOPLAY BUFFER] Finding similar songs to: {current_song.title} - {current_song.artist}")

        # Get similar songs based on current song
        songs = await ytmusic_player.get_similar_songs(current_song, count=1)

        if not songs:
            print(f"[AUTOPLAY BUFFER] No similar songs found, trying fallback...")
            # Fallback: try to get a popular song from pop genre
            songs = await ytmusic_player.get_random_songs_by_genre(
                "pop",
                count=1,
                requester=ctx.guild.me
            )
            if songs:
                print(f"[AUTOPLAY BUFFER] Using fallback pop song: {songs[0].title}")

        if not songs:
            print(f"[AUTOPLAY BUFFER] No songs available for buffering")
            return

        song = songs[0]

        # Verify stream URL is available before buffering
        stream_url = await ytmusic_player.get_stream_url(song.video_id)
        if stream_url:
            # Valid song - add to buffer
            ytmusic_player.set_buffer(ctx.guild.id, song)
            print(f"[AUTOPLAY BUFFER] Preloaded: {song.title} - {song.artist}")
        else:
            print(f"[AUTOPLAY BUFFER] Skipping {song.title} - no stream URL available")

    async def _auto_disconnect(self, ctx: commands.Context):
        """Auto disconnect after inactivity."""
        # Get auto-disconnect timeout from database (default 300 seconds = 5 minutes)
        timeout = config.AUTO_DISCONNECT_TIMEOUT  # Default from config
        if HAS_DATABASE:
            try:
                settings = db.get_guild_settings(ctx.guild.id)
                if settings and settings.get('auto_disconnect_time'):
                    timeout = settings['auto_disconnect_time']
            except Exception as e:
                print(f"Error loading auto_disconnect_time from DB: {e}")

        await asyncio.sleep(timeout)

        if ctx.voice_client and not ctx.voice_client.is_playing():
            await ctx.voice_client.disconnect()
            ytmusic_player.cleanup(ctx.guild.id)

            # Clean up all references
            if ctx.guild.id in self.now_playing_messages:
                del self.now_playing_messages[ctx.guild.id]
            if ctx.guild.id in self.now_playing_views:
                del self.now_playing_views[ctx.guild.id]
            if ctx.guild.id in self.song_start_times:
                del self.song_start_times[ctx.guild.id]
            self._cancel_progress_task(ctx.guild.id)

            embed = self._create_embed(
                "👋 Disconnected",
                "Bot telah disconnect karena tidak ada aktivitas.",
                config.COLORS["info"]
            )
            await ctx.send(embed=embed)

    async def _play_song(self, ctx: commands.Context, song: Song):
        """Play a song with smart message editing."""
        try:
            # Get fresh stream URL
            stream_url = await ytmusic_player.get_stream_url(song.video_id)

            if not stream_url:
                embed = self._create_embed(
                    "❌ Error",
                    f"Gagal mendapatkan stream URL untuk **{song.title}**",
                    config.COLORS["error"]
                )
                await ctx.send(embed=embed)
                self._play_next(ctx)
                return

            song.url = stream_url

            # Load volume from database (always check for dashboard changes)
            volume = None
            if HAS_DATABASE:
                try:
                    settings = db.get_guild_settings(ctx.guild.id)
                    if settings and settings.get('music_default_volume') is not None:
                        volume = settings['music_default_volume'] / 100  # Convert to 0.0-1.0
                except Exception as e:
                    print(f"Error loading volume from DB: {e}")

            # Fall back to current in-memory volume if database didn't have one
            if volume is None:
                volume = ytmusic_player.get_volume(ctx.guild.id)

            # Update in-memory volume to match what we're using
            ytmusic_player.set_volume(ctx.guild.id, volume)

            source = ytmusic_player.create_audio_source(stream_url, volume)

            ytmusic_player.now_playing[ctx.guild.id] = song

            # Record start time
            import time
            start_time = time.time()
            self.song_start_times[ctx.guild.id] = start_time

            ctx.voice_client.play(
                source,
                after=lambda e: self._play_next(ctx, e)
            )

            # Clear transitioning state now that song is playing
            ytmusic_player.set_transitioning(ctx.guild.id, False)

            # Preload next song if unlimited play is active (background task)
            if ytmusic_player.is_unlimited_play_active(ctx.guild.id):
                asyncio.create_task(self._preload_next_song(ctx))
            # Preload similar song if autoplay is active (background task)
            elif ytmusic_player.is_autoplay_active(ctx.guild.id):
                asyncio.create_task(self._preload_similar_song(ctx))

            # Check existing message and decide whether to edit or send new
            existing_message = self.now_playing_messages.get(ctx.guild.id)
            existing_view = self.now_playing_views.get(ctx.guild.id)

            # Calculate duration for progress bar (do this early for both cases)
            temp_view = MusicControlView(self, ctx)
            duration_seconds = temp_view._parse_duration(song.duration or "0")

            should_edit = False

            if existing_message and existing_view:
                # Check if we can edit the message (no user messages below)
                try:
                    has_new_messages = await self._has_messages_after(existing_message)
                    if not has_new_messages:
                        should_edit = True
                except discord.NotFound:
                    # Message was deleted
                    pass
                except Exception as e:
                    print(f"Error checking message status: {e}")

            if should_edit and existing_message and existing_view:
                # Update existing message
                existing_view.start_time = start_time
                existing_view.paused_duration = 0
                existing_view._elapsed_seconds = 0
                embed = existing_view._create_now_playing_embed(song, 0)
                await existing_message.edit(embed=embed, view=existing_view)

                # Start progress update task
                self._cancel_progress_task(ctx.guild.id)
                if duration_seconds > 0:
                    self.progress_tasks[ctx.guild.id] = asyncio.create_task(
                        self._update_progress(ctx.guild.id, existing_view, duration_seconds)
                    )
            else:
                # Delete old message if exists
                if existing_message:
                    try:
                        await existing_message.delete()
                    except:
                        pass

                # Create new message
                view = MusicControlView(self, ctx)
                view.start_time = start_time
                view._elapsed_seconds = 0

                embed = view._create_now_playing_embed(song, 0)

                message = await ctx.send(embed=embed, view=view)
                view.message = message

                # Store references
                self.now_playing_messages[ctx.guild.id] = message
                self.now_playing_views[ctx.guild.id] = view

                # Start progress update task
                self._cancel_progress_task(ctx.guild.id)
                if duration_seconds > 0:
                    self.progress_tasks[ctx.guild.id] = asyncio.create_task(
                        self._update_progress(ctx.guild.id, view, duration_seconds)
                    )
            
        except Exception as e:
            print(f"Error playing song: {e}")
            embed = self._create_embed(
                "❌ Error",
                f"Gagal memutar lagu: {str(e)}",
                config.COLORS["error"]
            )
            await ctx.send(embed=embed)
            self._play_next(ctx)

    async def _send_now_playing_message(self, ctx: commands.Context, song: Song):
        """Send/update now playing message without starting playback."""
        import time

        # Get current start time or create new
        start_time = self.song_start_times.get(ctx.guild.id, time.time())
        self.song_start_times[ctx.guild.id] = start_time

        # Get or create view
        view = self.now_playing_views.get(ctx.guild.id)
        if not view:
            view = MusicControlView(self, ctx)
            self.now_playing_views[ctx.guild.id] = view

        # Update view properties
        view.start_time = start_time
        view.ctx = ctx  # Update context in case it changed
        view._elapsed_seconds = 0

        # Calculate duration
        duration_seconds = view._parse_duration(song.duration or "0")

        # Create embed
        embed = view._create_now_playing_embed(song, 0)

        # Check if we should edit existing message or send new
        existing_message = self.now_playing_messages.get(ctx.guild.id)
        should_edit = False

        if existing_message:
            try:
                has_new_messages = await self._has_messages_after(existing_message)
                if not has_new_messages:
                    should_edit = True
            except discord.NotFound:
                pass
            except Exception as e:
                print(f"Error checking message status: {e}")

        if should_edit:
            # Edit existing message
            await existing_message.edit(embed=embed, view=view)
            view.message = existing_message
        else:
            # Delete old message if exists and send new
            if existing_message:
                try:
                    await existing_message.delete()
                except:
                    pass

            message = await ctx.send(embed=embed, view=view)
            view.message = message
            self.now_playing_messages[ctx.guild.id] = message

        # Start/restart progress update task
        self._cancel_progress_task(ctx.guild.id)
        if duration_seconds > 0:
            self.progress_tasks[ctx.guild.id] = asyncio.create_task(
                self._update_progress(ctx.guild.id, view, duration_seconds)
            )

    # ==================== PLAY COMMAND ====================
    @commands.command(name="play", aliases=["p"])
    async def play(self, ctx: commands.Context, *, query: str):
        """Cari dan mainkan lagu atau playlist dari YouTube Music atau Spotify."""
        if not await self._ensure_voice(ctx):
            return

        # Check if music is allowed in this channel
        if not await self._check_music_channel(ctx):
            return

        # Connect to voice channel first
        voice_client = await self._connect_voice(ctx)

        if not voice_client:
            embed = self._create_embed(
                "❌ Error",
                "Gagal connect ke voice channel!",
                config.COLORS["error"]
            )
            await ctx.send(embed=embed)
            return

        # Check if it's a Spotify URL (playlist or album)
        is_spotify = ytmusic_player._is_spotify_url(query)
        spotify_type = ytmusic_player._get_spotify_url_type(query) if is_spotify else None

        # Check if it's a playlist URL (YouTube or Spotify playlist/album)
        if ytmusic_player._is_playlist_url(query) or spotify_type in ('playlist', 'album'):
            # Determine playlist type for loading message
            if spotify_type == 'playlist':
                loading_text = "📂 Loading Spotify Playlist..."
            elif spotify_type == 'album':
                loading_text = "💿 Loading Spotify Album..."
            else:
                loading_text = "📂 Loading Playlist..."

            loading_embed = self._create_embed(
                loading_text,
                "Sedang memuat playlist, mohon tunggu...",
                config.COLORS["info"]
            )
            loading_msg = await ctx.send(embed=loading_embed)

            # Get songs based on URL type
            if spotify_type == 'playlist':
                songs = await ytmusic_player.get_spotify_playlist_songs(query, ctx.author)
            elif spotify_type == 'album':
                songs = await ytmusic_player.get_spotify_playlist_songs(query, ctx.author)
            else:
                songs = await ytmusic_player.get_playlist_songs(query, ctx.author)
            
            if not songs:
                error_msg = "Tidak dapat memuat playlist! Pastikan playlist bersifat publik."
                if spotify_type:
                    error_msg = "Fitur playlist/album Spotify belum tersedia. Untuk saat ini gunakan **single track link** saja.\n\nContoh: `!play https://open.spotify.com/track/xxx`"

                embed = self._create_embed(
                    "❌ Error",
                    error_msg,
                    config.COLORS["error"]
                )
                await loading_msg.edit(embed=embed)
                return

            # Add all songs to queue
            queue = ytmusic_player.get_queue(ctx.guild.id)

            # Check if unlimited play is active with buffer - prioritize user request
            is_unlimited_active = ytmusic_player.is_unlimited_play_active(ctx.guild.id)
            has_buffer = ytmusic_player.has_buffer(ctx.guild.id) if is_unlimited_active else False

            # Insert songs at front if unlimited play is active and buffer exists
            insert_at_front = is_unlimited_active and has_buffer and voice_client and (voice_client.is_playing() or voice_client.is_paused())

            if insert_at_front:
                # Insert songs at front in reverse order so first song is at position 1
                for song in reversed(songs):
                    queue.insert_at_front(song)
                print(f"[PRIORITY] Playlist with {len(songs)} songs inserted at front")
            else:
                for song in songs:
                    queue.add(song)

            await loading_msg.delete()

            # Set embed title based on source
            if spotify_type == 'album':
                embed_title = "💿 Album Loaded"
            elif spotify_type == 'playlist':
                embed_title = "📂 Spotify Playlist Loaded"
            else:
                embed_title = "📂 Playlist Loaded"

            # Check if we inserted at front for priority
            is_priority = is_unlimited_active and has_buffer and voice_client and (voice_client.is_playing() or voice_client.is_paused())

            if is_priority:
                description = f"Berhasil menambahkan **{len(songs)}** lagu ke queue!\n\n⭐ **Playing next (priority over unlimited play)**"
            else:
                description = f"Berhasil menambahkan **{len(songs)}** lagu ke queue!"

            embed = self._create_embed(
                embed_title,
                description,
                config.COLORS["success"]
            )
            embed.add_field(name="First Song", value=f"{songs[0].title} - {songs[0].artist}", inline=False)
            await ctx.send(embed=embed)

            # Start playing if not already
            if not voice_client.is_playing() and not voice_client.is_paused():
                first_song = queue.current_song
                if first_song:
                    # Enable autoplay automatically for user-requested playlist (so skip button always works)
                    if not is_unlimited_active:
                        ytmusic_player.set_autoplay(ctx.guild.id, True)
                        # Clear any existing buffer since the vibe is changing
                        ytmusic_player.clear_buffer(ctx.guild.id)
                        print(f"[AUTOPLAY] Automatically enabled for user-requested playlist (buffer cleared)")
                    await self._play_song(ctx, first_song)
            else:
                # Already playing - refresh now playing message
                # Clear buffer since user is adding new songs (vibe change)
                if not is_unlimited_active:
                    ytmusic_player.clear_buffer(ctx.guild.id)
                    print(f"[AUTOPLAY] Buffer cleared - user added playlist to queue")
                current_song = queue.current_song
                if current_song:
                    await self._send_now_playing_message(ctx, current_song)
        else:
            # Handle single song
            searching_embed = self._create_embed(
                "🔍 Searching...",
                f"Mencari: **{query}**",
                config.COLORS["info"]
            )
            searching_msg = await ctx.send(embed=searching_embed, delete_after=15)

            # Get song info
            song = await ytmusic_player.get_song_info(query, ctx.author)
            
            if not song:
                embed = self._create_embed(
                    "❌ Not Found",
                    f"Tidak dapat menemukan lagu: **{query}**",
                    config.COLORS["error"]
                )
                await searching_msg.edit(embed=embed)
                return

            # Add to queue
            queue = ytmusic_player.get_queue(ctx.guild.id)

            # Check if unlimited play is active with buffer - prioritize user request
            is_unlimited_active = ytmusic_player.is_unlimited_play_active(ctx.guild.id)
            has_buffer = ytmusic_player.has_buffer(ctx.guild.id) if is_unlimited_active else False

            if is_unlimited_active and has_buffer and voice_client and (voice_client.is_playing() or voice_client.is_paused()):
                # User request has priority - insert at front (position 1)
                position = queue.insert_at_front(song)
                print(f"[PRIORITY] User request inserted at front: {song.title}")
            else:
                # Normal add to end of queue
                position = queue.add(song)

            # Delete searching message
            await searching_msg.delete()

            # If not playing, start playing
            if not voice_client.is_playing() and not voice_client.is_paused():
                # Enable autoplay automatically for user-requested songs (so skip button always works)
                if not is_unlimited_active:
                    ytmusic_player.set_autoplay(ctx.guild.id, True)
                    # Clear any existing buffer since the vibe is changing
                    ytmusic_player.clear_buffer(ctx.guild.id)
                    print(f"[AUTOPLAY] Automatically enabled for user-requested song (buffer cleared)")
                await self._play_song(ctx, song)
            else:
                # Lagu sedang diputar, kirim now playing message ulang + added to queue
                # Clear buffer since user is adding a new song (vibe change)
                if not is_unlimited_active:
                    ytmusic_player.clear_buffer(ctx.guild.id)
                    print(f"[AUTOPLAY] Buffer cleared - user added new song to queue")
                current_song = queue.current_song
                if current_song:
                    await self._send_now_playing_message(ctx, current_song)

                # Show priority message if inserted at front
                if position == 1 and is_unlimited_active:
                    description = f"**[{song.title}]({song.youtube_url})**\nArtist: {song.artist}\n**⭐ Playing next (priority over unlimited play)**"
                else:
                    description = f"**[{song.title}]({song.youtube_url})**\nArtist: {song.artist}\nPosition: #{position}"

                embed = self._create_embed(
                    "✅ Added to Queue",
                    description,
                    config.COLORS["success"]
                )
                if song.thumbnail:
                    embed.set_thumbnail(url=song.thumbnail)
                await ctx.send(embed=embed)

    # ==================== PAUSE COMMAND ====================
    @commands.command(name="pause")
    async def pause(self, ctx: commands.Context):
        """Pause pemutaran musik."""
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            embed = self._create_embed(
                "❌ Error",
                "Tidak ada musik yang sedang diputar!",
                config.COLORS["error"]
            )
            return await self._send_with_auto_delete(ctx, embed)

        ctx.voice_client.pause()
        embed = self._create_embed(
            "⏸️ Paused",
            "Pemutaran musik telah di-pause.",
            config.COLORS["info"]
        )
        await self._send_with_auto_delete(ctx, embed)

    # ==================== RESUME COMMAND ====================
    @commands.command(name="resume", aliases=["unpause"])
    async def resume(self, ctx: commands.Context):
        """Resume pemutaran musik."""
        if not ctx.voice_client or not ctx.voice_client.is_paused():
            embed = self._create_embed(
                "❌ Error",
                "Tidak ada musik yang sedang di-pause!",
                config.COLORS["error"]
            )
            return await self._send_with_auto_delete(ctx, embed)

        ctx.voice_client.resume()
        embed = self._create_embed(
            "▶️ Resumed",
            "Pemutaran musik dilanjutkan.",
            config.COLORS["success"]
        )
        await self._send_with_auto_delete(ctx, embed)

    # ==================== SKIP COMMAND ====================
    @commands.command(name="skip", aliases=["s", "next"])
    async def skip(self, ctx: commands.Context):
        """Skip ke lagu berikutnya."""
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            embed = self._create_embed(
                "❌ Error",
                "Tidak ada musik yang sedang diputar!",
                config.COLORS["error"]
            )
            return await self._send_with_auto_delete(ctx, embed)

        ctx.voice_client.stop()  # This will trigger _play_next
        embed = self._create_embed(
            "⏭️ Skipped",
            "Lagu telah di-skip.",
            config.COLORS["info"]
        )
        await self._send_with_auto_delete(ctx, embed)

    # ==================== STOP COMMAND ====================
    @commands.command(name="stop", aliases=["disconnect", "dc", "leave"])
    async def stop(self, ctx: commands.Context):
        """Stop pemutaran dan disconnect dari voice channel."""
        if not ctx.voice_client:
            embed = self._create_embed(
                "❌ Error",
                "Bot tidak ada di voice channel!",
                config.COLORS["error"]
            )
            return await self._send_with_auto_delete(ctx, embed)

        # Clear queue and disconnect
        ytmusic_player.cleanup(ctx.guild.id)
        await ctx.voice_client.disconnect()

        embed = self._create_embed(
            "👋 Disconnected",
            "Bot telah disconnect dan queue telah dikosongkan.",
            config.COLORS["info"]
        )
        await self._send_with_auto_delete(ctx, embed)

    # ==================== QUEUE COMMAND ====================
    @commands.command(name="queue", aliases=["q"])
    async def queue(self, ctx: commands.Context):
        """Tampilkan antrian lagu dengan pagination."""
        queue = ytmusic_player.get_queue(ctx.guild.id)

        if not queue.songs:
            embed = self._create_embed(
                "📜 Queue",
                "Queue kosong! Gunakan `!play <lagu>` untuk menambah lagu.",
                config.COLORS["info"]
            )
            return await self._send_with_auto_delete(ctx, embed)

        # Create pagination view
        view = QueuePaginationView(ctx.guild.id, page=0)
        await ctx.send(embed=view.get_embed(), view=view)

    # ==================== NOW PLAYING COMMAND ====================
    @commands.command(name="nowplaying", aliases=["np", "current"])
    async def nowplaying(self, ctx: commands.Context):
        """Tampilkan lagu yang sedang diputar."""
        current = ytmusic_player.now_playing.get(ctx.guild.id)
        
        if not current:
            embed = self._create_embed(
                "❌ Error",
                "Tidak ada lagu yang sedang diputar!",
                config.COLORS["error"]
            )
            return await self._send_with_auto_delete(ctx, embed)

        embed = self._create_now_playing_embed(current, ctx.guild.id)
        await ctx.send(embed=embed)

    # ==================== VOLUME COMMAND ====================
    @commands.command(name="volume", aliases=["vol", "v"])
    async def volume(self, ctx: commands.Context, volume: int = None):
        """Atur volume (0-100)."""
        if volume is None:
            current_vol = int(ytmusic_player.get_volume(ctx.guild.id) * 100)
            embed = self._create_embed(
                "🔊 Volume",
                f"Volume saat ini: **{current_vol}%**",
                config.COLORS["info"]
            )
            return await self._send_with_auto_delete(ctx, embed)

        if volume < 0 or volume > 100:
            embed = self._create_embed(
                "❌ Error",
                "Volume harus antara 0 dan 100!",
                config.COLORS["error"]
            )
            return await self._send_with_auto_delete(ctx, embed)

        ytmusic_player.set_volume(ctx.guild.id, volume / 100)

        # Save to database
        if HAS_DATABASE:
            try:
                db.update_guild_settings(ctx.guild.id, {'music_default_volume': volume})
            except Exception as e:
                print(f"Error saving volume to DB: {e}")

        # Update current source volume if playing
        if ctx.voice_client and ctx.voice_client.source:
            ctx.voice_client.source.volume = volume / 100

        embed = self._create_embed(
            "🔊 Volume Set",
            f"Volume telah diatur ke **{volume}%**",
            config.COLORS["success"]
        )
        await self._send_with_auto_delete(ctx, embed)

    # ==================== SHUFFLE COMMAND ====================
    @commands.command(name="shuffle")
    async def shuffle(self, ctx: commands.Context):
        """Acak antrian lagu."""
        queue = ytmusic_player.get_queue(ctx.guild.id)
        
        if len(queue) < 2:
            embed = self._create_embed(
                "❌ Error",
                "Tidak cukup lagu dalam queue untuk di-shuffle!",
                config.COLORS["error"]
            )
            return await ctx.send(embed=embed)

        queue.shuffle()
        embed = self._create_embed(
            "🔀 Shuffled",
            "Queue telah diacak!",
            config.COLORS["success"]
        )
        await self._send_with_auto_delete(ctx, embed)

    # ==================== LOOP COMMAND ====================
    @commands.command(name="loop", aliases=["repeat"])
    async def loop(self, ctx: commands.Context, mode: str = None):
        """
        Toggle loop mode.
        Mode: off, one/single, all/queue
        """
        queue = ytmusic_player.get_queue(ctx.guild.id)

        if mode is None:
            # Cycle through modes: off -> single -> all -> off
            if not queue.loop and not queue.loop_single:
                queue.loop_single = True
                status = "Single 🔂"
            elif queue.loop_single:
                queue.loop_single = False
                queue.loop = True
                status = "All 🔁"
            else:
                queue.loop = False
                status = "Off"
        elif mode.lower() in ["off", "none"]:
            queue.loop = False
            queue.loop_single = False
            status = "Off"
        elif mode.lower() in ["one", "single", "1"]:
            queue.loop_single = True
            queue.loop = False
            status = "Single 🔂"
        elif mode.lower() in ["all", "queue"]:
            queue.loop = True
            queue.loop_single = False
            status = "All 🔁"
        else:
            embed = self._create_embed(
                "❌ Error",
                "Mode tidak valid! Gunakan: `off`, `one`, atau `all`",
                config.COLORS["error"]
            )
            return await ctx.send(embed=embed)

        embed = self._create_embed(
            "🔁 Loop Mode",
            f"Loop mode: **{status}**",
            config.COLORS["info"]
        )
        await self._send_with_auto_delete(ctx, embed)

    # ==================== REMOVE COMMAND ====================
    @commands.command(name="remove", aliases=["rm"])
    async def remove(self, ctx: commands.Context, index: int):
        """Hapus lagu dari queue berdasarkan posisi."""
        queue = ytmusic_player.get_queue(ctx.guild.id)

        # Index 1 = first upcoming song (songs[1])
        # Cannot remove current song (index 0)
        if index < 1:
            embed = self._create_embed(
                "❌ Error",
                "Tidak dapat menghapus lagu yang sedang diputar! Gunakan `!skip` untuk mengganti lagu.",
                config.COLORS["error"]
            )
            return await ctx.send(embed=embed)

        if index >= len(queue.songs):
            embed = self._create_embed(
                "❌ Error",
                "Index tidak valid! Queue hanya memiliki {} lagu.".format(len(queue.songs)),
                config.COLORS["error"]
            )
            return await ctx.send(embed=embed)

        # Remove the song at given index (index 1 = songs[1])
        removed = queue.remove(index)

        if removed:
            embed = self._create_embed(
                "🗑️ Removed",
                f"**{removed.title}** telah dihapus dari queue.",
                config.COLORS["success"]
            )
        else:
            embed = self._create_embed(
                "❌ Error",
                "Gagal menghapus lagu!",
                config.COLORS["error"]
            )

        await self._send_with_auto_delete(ctx, embed)

    # ==================== CLEAR QUEUE COMMAND ====================
    @commands.command(name="clear_queue", aliases=["clearqueue", "cq"])
    async def clear_queue(self, ctx: commands.Context):
        """Hapus lagu terakhir dari queue."""
        queue = ytmusic_player.get_queue(ctx.guild.id)

        if len(queue.songs) <= 1:  # Only current song or empty
            embed = self._create_embed(
                "❌ Error",
                "Tidak ada lagu dalam queue untuk dihapus!",
                config.COLORS["error"]
            )
            return await ctx.send(embed=embed)

        # Remove the last song (most recently added) - songs[0] is current
        removed_song = queue.songs.pop()
        embed = self._create_embed(
            "🗑️ Lagu Terakhir Dihapus",
            f"Menghapus: **{removed_song.title}**",
            config.COLORS["success"]
        )
        await self._send_with_auto_delete(ctx, embed)

    # ==================== SEARCH COMMAND ====================
    @commands.command(name="search")
    async def search(self, ctx: commands.Context, *, query: str):
        """Cari lagu dan pilih dari hasil."""
        searching_embed = self._create_embed(
            "🔍 Searching...",
            f"Mencari: **{query}**",
            config.COLORS["info"]
        )
        searching_msg = await ctx.send(embed=searching_embed)

        results = await ytmusic_player.search(query, limit=5)
        
        if not results:
            embed = self._create_embed(
                "❌ Not Found",
                f"Tidak dapat menemukan: **{query}**",
                config.COLORS["error"]
            )
            return await searching_msg.edit(embed=embed)

        # Build results list
        description = ""
        for i, result in enumerate(results, 1):
            title = result.get('title', 'Unknown')
            artists = result.get('artists', [])
            artist = artists[0].get('name', 'Unknown') if artists else 'Unknown'
            duration = result.get('duration', 'Unknown')
            description += f"`{i}.` **{title}** - {artist} ({duration})\n"

        description += "\n*Ketik nomor (1-5) untuk memilih, atau `cancel` untuk batal.*"

        embed = self._create_embed(
            f"🔍 Search Results: {query}",
            description,
            config.COLORS["music"]
        )
        await searching_msg.edit(embed=embed)

        # Wait for user response
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', timeout=30.0, check=check)
            
            if msg.content.lower() == 'cancel':
                embed = self._create_embed(
                    "❌ Cancelled",
                    "Pencarian dibatalkan.",
                    config.COLORS["info"]
                )
                return await ctx.send(embed=embed)

            try:
                choice = int(msg.content)
                if 1 <= choice <= len(results):
                    selected = results[choice - 1]
                    video_id = selected.get('videoId', '')
                    
                    # Play the selected song
                    await ctx.invoke(self.play, query=f"https://www.youtube.com/watch?v={video_id}")
                else:
                    embed = self._create_embed(
                        "❌ Error",
                        "Pilihan tidak valid!",
                        config.COLORS["error"]
                    )
                    await ctx.send(embed=embed)
            except ValueError:
                embed = self._create_embed(
                    "❌ Error",
                    "Masukkan nomor yang valid!",
                    config.COLORS["error"]
                )
                await ctx.send(embed=embed)
                
        except asyncio.TimeoutError:
            embed = self._create_embed(
                "⏱️ Timeout",
                "Waktu habis! Pencarian dibatalkan.",
                config.COLORS["warning"]
            )
            await ctx.send(embed=embed)

    # ==================== GENRE SELECT VIEW ====================
    class GenreSelectView(ui.View):
        """Dropdown menu untuk genre selection."""

        # Default genres
        DEFAULT_GENRES = [
            discord.SelectOption(label="Pop", emoji="🎤", value="pop", description="Top pop hits"),
            discord.SelectOption(label="Rock", emoji="🎸", value="rock", description="Classic & modern rock"),
            discord.SelectOption(label="Hip-Hop", emoji="🎧", value="hip-hop", description="Hip-hop & rap"),
            discord.SelectOption(label="EDM", emoji="🎹", value="edm", description="Electronic dance music"),
            discord.SelectOption(label="Jazz", emoji="🎷", value="jazz", description="Jazz classics"),
            discord.SelectOption(label="Classical", emoji="🎻", value="classical", description="Classical music"),
            discord.SelectOption(label="K-Pop", emoji="🌟", value="k-pop", description="Korean pop"),
            discord.SelectOption(label="R&B", emoji="🎤", value="rnb", description="R&B soul"),
            discord.SelectOption(label="Country", emoji="🤠", value="country", description="Country hits"),
            discord.SelectOption(label="Lo-Fi", emoji="☕", value="lofi", description="Lo-fi beats"),
            discord.SelectOption(label="Indie", emoji="🌿", value="indie", description="Indie music"),
        ]

        def __init__(self, cog: 'Music', ctx: commands.Context, count: int = 5):
            super().__init__(timeout=60)
            self.cog = cog
            self.ctx = ctx
            self.count = count
            self.user_id = ctx.author.id
            self.genre_select = None
            self._build_select_menu()

        def _build_select_menu(self):
            """Build the select menu with default and user custom genres."""
            # Start with default genres
            options = self.DEFAULT_GENRES.copy()

            # Add user's custom genres if available
            if HAS_DATABASE:
                try:
                    user_genres = db.get_user_genres(self.user_id)
                    for genre in user_genres:
                        options.append(
                            discord.SelectOption(
                                label=f"[Custom] {genre['genre_name']}",
                                emoji=genre.get('emoji', '🎵'),
                                value=f"custom_{genre['id']}",
                                description=genre['search_query']
                            )
                        )
                except Exception as e:
                    print(f"[ERROR] Failed to load user genres: {e}")

            # Create the select menu
            self.genre_select = ui.Select(
                min_values=1,
                max_values=1,
                placeholder="Pilih genre...",
                options=options[:25]  # Discord limit is 25 options
            )
            self.genre_select.callback = self._select_callback
            self.add_item(self.genre_select)

        async def _select_callback(self, interaction: discord.Interaction):
            """Handle genre selection."""
            select = self.genre_select
            genre_value = select.values[0]

            # Check if it's a custom genre
            search_query = None
            genre_display = genre_value

            if genre_value.startswith("custom_"):
                # Extract genre ID
                genre_id = int(genre_value.replace("custom_", ""))
                if HAS_DATABASE:
                    try:
                        genre_data = db.get_user_genre_by_id(self.user_id, genre_id)
                        if genre_data:
                            search_query = genre_data['search_query']
                            genre_display = genre_data['genre_name']
                        else:
                            await interaction.response.send_message(
                                "❌ Genre tidak ditemukan. Mungkin sudah dihapus.",
                                ephemeral=True
                            )
                            return
                    except Exception as e:
                        print(f"[ERROR] Failed to get user genre: {e}")
                        await interaction.response.send_message(
                            "❌ Gagal memuat genre.",
                            ephemeral=True
                        )
                        return
                else:
                    await interaction.response.send_message(
                        "❌ Database tidak tersedia.",
                        ephemeral=True
                    )
                    return
            else:
                # Default genre
                search_query = None

            # Defer response
            await interaction.response.defer()

            # Get random songs from selected genre
            songs = await ytmusic_player.get_random_songs_by_genre(
                search_query or genre_value,
                count=self.count,
                requester=self.ctx.author
            )

            if not songs:
                await interaction.followup.send(
                    f"❌ Tidak ada lagu ditemukan untuk genre: **{genre_display}**",
                    ephemeral=True
                )
                return

            # Add songs to queue
            queue = ytmusic_player.get_queue(self.ctx.guild.id)

            # Check if unlimited play is active with buffer - prioritize user request
            is_unlimited_active = ytmusic_player.is_unlimited_play_active(self.ctx.guild.id)
            has_buffer = ytmusic_player.has_buffer(self.ctx.guild.id) if is_unlimited_active else False

            vc = self.ctx.voice_client
            insert_at_front = is_unlimited_active and has_buffer and vc and (vc.is_playing() or vc.is_paused())

            if insert_at_front:
                # Insert songs at front in reverse order so first song is at position 1
                for song in reversed(songs):
                    queue.insert_at_front(song)
                print(f"[PRIORITY] rplay with {len(songs)} songs inserted at front")
            else:
                for song in songs:
                    queue.add(song)

            # Send confirmation
            # Check if we inserted at front for priority
            is_priority = is_unlimited_active and has_buffer and vc and (vc.is_playing() or vc.is_paused())

            if is_priority:
                description = f"Berhasil menambahkan **{len(songs)}** lagu random {genre_display} ke queue!\n\n⭐ **Playing next (priority over unlimited play)**"
            else:
                description = f"Berhasil menambahkan **{len(songs)}** lagu random {genre_display} ke queue!"

            embed = discord.Embed(
                title=f"🎵 {genre_display.title()} Added",
                description=description,
                color=config.COLORS["music"]
            )

            # Show first few songs
            song_list = "\n".join([
                f"**{i+1}.** {song.title} - {song.artist}"
                for i, song in enumerate(songs[:5])
            ])

            if len(songs) > 5:
                song_list += f"\n*... dan {len(songs) - 5} lagu lainnya*"

            embed.add_field(name="Lagu", value=song_list, inline=False)

            if songs[0].thumbnail:
                embed.set_thumbnail(url=songs[0].thumbnail)

            await interaction.followup.send(embed=embed)

            # Start playing if not already
            vc = self.ctx.voice_client
            if vc and not vc.is_playing() and not vc.is_paused():
                await self.cog._play_song(self.ctx, queue.current_song)
            elif vc and (vc.is_playing() or vc.is_paused()):
                # Already playing - refresh now playing message
                current_song = queue.current_song
                if current_song:
                    await self.cog._send_now_playing_message(self.ctx, current_song)

            # Disable the select menu
            select.disabled = True
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)

        @ui.button(label="Cancel", style=discord.ButtonStyle.secondary, row=1)
        async def cancel_button(self, interaction: discord.Interaction, _button: ui.Button):
            """Cancel the selection."""
            await interaction.response.edit_message(
                content="❌ Dibatalkan",
                view=None
            )
            self.stop()

    # ==================== RANDOM PLAY COMMAND ====================
    @commands.command(name="rplay", aliases=["randomplay", "rp"])
    async def random_play(self, ctx: commands.Context, count: int = 5):
        """
        Putar lagu random dari genre yang dipilih.

        Usage: !rplay [count]
        count: Jumlah lagu (default: 5, max: 20)
        """
        if not await self._ensure_voice(ctx):
            return

        # Validate count
        count = max(1, min(20, count))

        # Connect to voice
        await self._connect_voice(ctx)

        # Create and send genre selection view
        view = self.GenreSelectView(self, ctx, count)

        embed = discord.Embed(
            title="🎵 Pilih Genre",
            description=f"Pilih genre untuk memutar **{count}** lagu random!",
            color=config.COLORS["music"]
        )

        embed.add_field(
            name="Cara kerja",
            value="Pilih genre dari dropdown dan bot akan menambahkan lagu random dari genre tersebut ke queue.",
            inline=False
        )

        await ctx.send(embed=embed, view=view)

    # ==================== UNLIMITED PLAY COMMAND ====================
    @commands.command(name="uplay", aliases=["unlimitedplay", "up"])
    async def unlimited_play(self, ctx: commands.Context, *, genre: str = None):
        """
        Unlimited play - putar lagu random dari genre terus menerus.

        Usage: !uplay [genre]
        !uplay stop - Stop unlimited play tanpa memotong lagu
        Jika genre tidak dispesifikasikan, akan menampilkan dropdown.
        """
        # Handle !uplay stop
        if genre and genre.lower() == "stop":
            if ytmusic_player.is_unlimited_play_active(ctx.guild.id):
                old_genre = ytmusic_player.get_unlimited_genre(ctx.guild.id)
                ytmusic_player.clear_unlimited_play(ctx.guild.id)

                embed = discord.Embed(
                    title="🛑 Unlimited Play Dihentikan",
                    description=f"Unlimited play untuk genre **{old_genre.title()}** telah dihentikan.",
                    color=config.COLORS["info"]
                )

                queue = ytmusic_player.get_queue(ctx.guild.id)
                if queue.songs:
                    embed.add_field(
                        name="Info",
                        value=f"Lagu saat ini akan terus diputar. Queue tetap ada (**{len(queue)} lagu**).",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="Info",
                        value="Lagu saat ini akan terus diputar. Bot akan disconnect setelah lagu selesai.",
                        inline=False
                    )

                await ctx.send(embed=embed, delete_after=5)
            else:
                embed = self._create_embed(
                    "ℹ️ Info",
                    "Tidak ada unlimited play yang sedang aktif.",
                    config.COLORS["info"]
                )
                await ctx.send(embed=embed, delete_after=5)
            return

        if not await self._ensure_voice(ctx):
            return

        await self._connect_voice(ctx)

        if genre is None:
            # Show genre dropdown
            view = self.UnlimitedGenreSelectView(self, ctx)
            embed = discord.Embed(
                title="🎵 Pilih Genre untuk Unlimited Play",
                description="Pilih genre dan bot akan memutar lagu random dari genre tersebut **secara terus-menerus**!",
                color=config.COLORS["music"]
            )
            embed.add_field(
                name="Cara kerja",
                value="Bot akan memutar 1 lagu, dan setelah selesai otomatis menambah lagu baru. Queue tetap kosong. Hanya berhenti saat tombol Stop ditekan.",
                inline=False
            )
            await ctx.send(embed=embed, view=view)
        else:
            # Map genre name to API format
            genre_mapping = {
                "pop": "pop", "rock": "rock", "hiphop": "hip-hop", "hip-hop": "hip-hop",
                "edm": "edm", "jazz": "jazz", "classical": "classical",
                "kpop": "k-pop", "k-pop": "k-pop", "rnb": "rnb", "r&b": "rnb",
                "country": "country", "lofi": "lofi", "lo-fi": "lofi", "indie": "indie"
            }
            api_genre = genre_mapping.get(genre.lower(), genre.lower())

            # Get 1 random song from genre
            await self._start_unlimited_play(ctx, api_genre)

    async def _start_unlimited_play(self, ctx: commands.Context, genre: str):
        """Start unlimited play with given genre."""
        guild_id = ctx.guild.id

        # Check if unlimited play is already active
        if ytmusic_player.is_unlimited_play_active(guild_id):
            current_genre = ytmusic_player.get_unlimited_genre(guild_id)
            if current_genre.lower() == genre.lower():
                # Same genre, just inform user
                embed = self._create_embed(
                    "ℹ️ Unlimited Play Sudah Aktif",
                    f"Unlimited play untuk genre **{genre.title()}** sudah berjalan!",
                    config.COLORS["info"]
                )
                await ctx.send(embed=embed, delete_after=5)
                return
            else:
                # Different genre, ask for confirmation
                view = self.ChangeGenreConfirmView(self, ctx, genre)
                embed = discord.Embed(
                    title="⚠️ Ganti Genre Unlimited Play?",
                    description=f"Unlimited play sedang aktif dengan genre **{current_genre.title()}**.\n\nApakah Anda ingin mengganti ke **{genre.title()}**?",
                    color=config.COLORS["info"]
                )
                embed.add_field(
                    name="Info",
                    value="Genre akan berubah setelah lagu saat ini selesai.",
                    inline=False
                )
                await ctx.send(embed=embed, view=view)
                return

        # Get 1 random song from genre
        song = await ytmusic_player.get_random_songs_by_genre(
            genre,
            count=1,
            requester=ctx.author
        )

        if not song:
            embed = self._create_embed(
                "❌ Genre Not Found",
                f"Tidak dapat menemukan lagu untuk genre: **{genre}**",
                config.COLORS["error"]
            )
            return await ctx.send(embed=embed)

        song = song[0]  # Get first (and only) song

        # Verify stream URL is available before playing
        stream_url = await ytmusic_player.get_stream_url(song.video_id)
        if not stream_url:
            embed = self._create_embed(
                "❌ Error",
                f"Gagal mendapatkan stream URL untuk **{song.title}**. Mencoba lagu lain...",
                config.COLORS["error"]
            )
            await ctx.send(embed=embed, delete_after=5)
            # Try to get another song recursively
            await self._play_unlimited_song(ctx, genre)
            return

        # Enable unlimited play mode
        ytmusic_player.set_unlimited_play(guild_id, genre)
        # Disable autoplay when unlimited play starts (avoid conflicts)
        ytmusic_player.set_autoplay(guild_id, False)

        # Add to queue
        queue = ytmusic_player.get_queue(guild_id)
        queue.add(song)

        # Check if already playing
        vc = ctx.voice_client
        is_playing_now = False
        if vc and (vc.is_playing() or vc.is_paused()):
            # Already playing - just update now playing message and confirm
            # Song will play naturally after current song finishes
            current_song = queue.current_song
            if current_song:
                await self._send_now_playing_message(ctx, current_song)
            # Preload next song for unlimited play
            asyncio.create_task(self._preload_next_song(ctx))
        else:
            # Not playing - start playback
            await self._play_song(ctx, song)
            is_playing_now = True

        # Send confirmation
        if is_playing_now:
            description = f"Memutar **{song.title}** - {song.artist}"
        else:
            # Check position in queue
            position = len(queue.upcoming)
            if position == 0:
                description = f"Berikutnya: **{song.title}** - {song.artist}"
            else:
                description = f" Ditambahkan ke queue (**#{position}**): **{song.title}** - {song.artist}"

        embed = discord.Embed(
            title=f"🎵 Unlimited Play: {genre.title()}",
            description=description,
            color=config.COLORS["music"]
        )
        embed.add_field(
            name="Mode Unlimited",
            value="Bot akan terus memutar lagu random dari genre ini. Tekan tombol ⏹️ untuk berhenti.",
            inline=False
        )
        if song.thumbnail:
            embed.set_thumbnail(url=song.thumbnail)
        await ctx.send(embed=embed)

    async def _start_unlimited_play_with_genre(self, ctx: commands.Context, search_query: str, genre_display: str):
        """Start unlimited play with custom genre (search_query)."""
        guild_id = ctx.guild.id

        # Check if unlimited play is already active
        if ytmusic_player.is_unlimited_play_active(guild_id):
            current_genre = ytmusic_player.get_unlimited_genre(guild_id)
            if current_genre.lower() == search_query.lower():
                # Same genre, just inform user
                embed = self._create_embed(
                    "ℹ️ Unlimited Play Sudah Aktif",
                    f"Unlimited play untuk genre **{genre_display.title()}** sudah berjalan!",
                    config.COLORS["info"]
                )
                await ctx.send(embed=embed, delete_after=5)
                return
            else:
                # Different genre, ask for confirmation
                view = self.ChangeGenreConfirmView(self, ctx, search_query, genre_display)
                embed = discord.Embed(
                    title="⚠️ Ganti Genre Unlimited Play?",
                    description=f"Unlimited play sedang aktif dengan genre **{current_genre.title()}**.\n\nApakah Anda ingin mengganti ke **{genre_display.title()}**?",
                    color=config.COLORS["info"]
                )
                embed.add_field(
                    name="Info",
                    value="Genre akan berubah setelah lagu saat ini selesai.",
                    inline=False
                )
                await ctx.send(embed=embed, view=view)
                return

        # Get 1 random song from genre
        song = await ytmusic_player.get_random_songs_by_genre(
            search_query,
            count=1,
            requester=ctx.author
        )

        if not song:
            embed = self._create_embed(
                "❌ Genre Not Found",
                f"Tidak dapat menemukan lagu untuk genre: **{genre_display}**",
                config.COLORS["error"]
            )
            return await ctx.send(embed=embed)

        song = song[0]  # Get first (and only) song

        # Verify stream URL is available before playing
        stream_url = await ytmusic_player.get_stream_url(song.video_id)
        if not stream_url:
            embed = self._create_embed(
                "❌ Error",
                f"Gagal mendapatkan stream URL untuk **{song.title}**. Mencoba lagu lain...",
                config.COLORS["error"]
            )
            await ctx.send(embed=embed, delete_after=5)
            # Try to get another song recursively
            await self._play_unlimited_song_with_genre(ctx, search_query)
            return

        # Enable unlimited play mode with search_query
        ytmusic_player.set_unlimited_play(guild_id, search_query)
        # Disable autoplay when unlimited play starts (avoid conflicts)
        ytmusic_player.set_autoplay(guild_id, False)

        # Add to queue
        queue = ytmusic_player.get_queue(guild_id)
        queue.add(song)

        # Check if already playing
        vc = ctx.voice_client
        is_playing_now = False
        if vc and (vc.is_playing() or vc.is_paused()):
            # Already playing - just update now playing message and confirm
            # Song will play naturally after current song finishes
            current_song = queue.current_song
            if current_song:
                await self._send_now_playing_message(ctx, current_song)
            # Preload next song for unlimited play
            asyncio.create_task(self._preload_next_song_with_genre(ctx, search_query))
        else:
            # Not playing - start playback
            await self._play_song(ctx, song)
            is_playing_now = True

        # Send confirmation
        if is_playing_now:
            description = f"Memutar **{song.title}** - {song.artist}"
        else:
            # Check position in queue
            position = len(queue.upcoming)
            if position == 0:
                description = f"Berikutnya: **{song.title}** - {song.artist}"
            else:
                description = f" Ditambahkan ke queue (**#{position}**): **{song.title}** - {song.artist}"

        embed = discord.Embed(
            title=f"🎵 Unlimited Play: {genre_display.title()}",
            description=description,
            color=config.COLORS["music"]
        )
        embed.add_field(
            name="Mode Unlimited",
            value="Bot akan terus memutar lagu random dari genre ini. Tekan tombol ⏹️ untuk berhenti.",
            inline=False
        )
        if song.thumbnail:
            embed.set_thumbnail(url=song.thumbnail)
        await ctx.send(embed=embed)

    async def _preload_next_song_with_genre(self, ctx: commands.Context, search_query: str):
        """Preload the next song for unlimited play with custom genre."""
        try:
            song = await ytmusic_player.get_random_songs_by_genre(
                search_query,
                count=1,
                requester=ctx.author
            )
            if song:
                song = song[0]
                ytmusic_player.set_buffer(ctx.guild.id, song)
                print(f"[UNLIMITED] Preloaded next song: {song.title}")
        except Exception as e:
            print(f"[ERROR] Failed to preload next song: {e}")

    async def _play_unlimited_song_with_genre(self, ctx: commands.Context, search_query: str):
        """Play next unlimited song with custom genre."""
        try:
            song = await ytmusic_player.get_random_songs_by_genre(
                search_query,
                count=1,
                requester=ctx.author
            )
            if song:
                song = song[0]
                ytmusic_player.set_buffer(ctx.guild.id, song)
                queue = ytmusic_player.get_queue(ctx.guild.id)
                queue.add(song)
        except Exception as e:
            print(f"[ERROR] Failed to play unlimited song: {e}")

    class ChangeGenreConfirmView(ui.View):
        """Confirmation view untuk mengganti unlimited play genre."""

        def __init__(self, cog: 'Music', ctx: commands.Context, new_genre: str, genre_display: str = None):
            super().__init__(timeout=30)
            self.cog = cog
            self.ctx = ctx
            self.new_genre = new_genre
            self.genre_display = genre_display or new_genre

        @ui.button(label="Ya, Ganti Genre", style=discord.ButtonStyle.danger, emoji="✅")
        async def confirm_button(self, interaction: discord.Interaction, _button: ui.Button):
            """Confirm genre change."""
            # Update unlimited play genre
            ytmusic_player.set_unlimited_play(self.ctx.guild.id, self.new_genre)
            # Disable autoplay when unlimited play starts (avoid conflicts)
            ytmusic_player.set_autoplay(self.ctx.guild.id, False)

            # Clear old buffer and preload new genre song
            ytmusic_player.clear_buffer(self.ctx.guild.id)

            # Use appropriate preload function based on whether it's custom genre
            if hasattr(self, 'genre_display') and self.genre_display != self.new_genre:
                asyncio.create_task(self.cog._preload_next_song_with_genre(self.ctx, self.new_genre))
            else:
                asyncio.create_task(self.cog._preload_next_song(self.ctx))

            await interaction.response.edit_message(
                embed=discord.Embed(
                    title="✅ Genre Berubah",
                    description=f"Unlimited play akan menggunakan genre **{self.genre_display.title()}** setelah lagu ini selesai.",
                    color=config.COLORS["success"]
                ),
                view=None
            )

        @ui.button(label="Batal", style=discord.ButtonStyle.secondary, emoji="❌")
        async def cancel_button(self, interaction: discord.Interaction, _button: ui.Button):
            """Cancel genre change."""
            current_genre = ytmusic_player.get_unlimited_genre(self.ctx.guild.id)
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title="❌ Batal",
                    description=f"Unlimited play tetap menggunakan genre **{current_genre.title()}**.",
                    color=config.COLORS["info"]
                ),
                view=None
            )

    class UnlimitedGenreSelectView(ui.View):
        """Dropdown menu untuk unlimited play genre selection."""

        # Default genres (same as GenreSelectView)
        DEFAULT_GENRES = [
            discord.SelectOption(label="Pop", emoji="🎤", value="pop", description="Top pop hits"),
            discord.SelectOption(label="Rock", emoji="🎸", value="rock", description="Classic & modern rock"),
            discord.SelectOption(label="Hip-Hop", emoji="🎧", value="hip-hop", description="Hip-hop & rap"),
            discord.SelectOption(label="EDM", emoji="🎹", value="edm", description="Electronic dance music"),
            discord.SelectOption(label="Jazz", emoji="🎷", value="jazz", description="Jazz classics"),
            discord.SelectOption(label="Classical", emoji="🎻", value="classical", description="Classical music"),
            discord.SelectOption(label="K-Pop", emoji="🌟", value="k-pop", description="Korean pop"),
            discord.SelectOption(label="R&B", emoji="🎤", value="rnb", description="R&B soul"),
            discord.SelectOption(label="Country", emoji="🤠", value="country", description="Country hits"),
            discord.SelectOption(label="Lo-Fi", emoji="☕", value="lofi", description="Lo-fi beats"),
            discord.SelectOption(label="Indie", emoji="🌿", value="indie", description="Indie music"),
        ]

        def __init__(self, cog: 'Music', ctx: commands.Context):
            super().__init__(timeout=60)
            self.cog = cog
            self.ctx = ctx
            self.user_id = ctx.author.id
            self.genre_select = None
            self._build_select_menu()

        def _build_select_menu(self):
            """Build the select menu with default and user custom genres."""
            # Start with default genres
            options = self.DEFAULT_GENRES.copy()

            # Add user's custom genres if available
            if HAS_DATABASE:
                try:
                    user_genres = db.get_user_genres(self.user_id)
                    for genre in user_genres:
                        options.append(
                            discord.SelectOption(
                                label=f"[Custom] {genre['genre_name']}",
                                emoji=genre.get('emoji', '🎵'),
                                value=f"custom_{genre['id']}",
                                description=genre['search_query']
                            )
                        )
                except Exception as e:
                    print(f"[ERROR] Failed to load user genres: {e}")

            # Create the select menu
            self.genre_select = ui.Select(
                min_values=1,
                max_values=1,
                placeholder="Pilih genre untuk unlimited play...",
                options=options[:25]  # Discord limit is 25 options
            )
            self.genre_select.callback = self._select_callback
            self.add_item(self.genre_select)

        async def _select_callback(self, interaction: discord.Interaction):
            """Handle genre selection for unlimited play."""
            select = self.genre_select
            genre_value = select.values[0]

            # Check if it's a custom genre
            search_query = None
            genre_display = genre_value

            if genre_value.startswith("custom_"):
                # Extract genre ID
                genre_id = int(genre_value.replace("custom_", ""))
                if HAS_DATABASE:
                    try:
                        genre_data = db.get_user_genre_by_id(self.user_id, genre_id)
                        if genre_data:
                            search_query = genre_data['search_query']
                            genre_display = genre_data['genre_name']
                        else:
                            await interaction.response.send_message(
                                "❌ Genre tidak ditemukan. Mungkin sudah dihapus.",
                                ephemeral=True
                            )
                            return
                    except Exception as e:
                        print(f"[ERROR] Failed to get user genre: {e}")
                        await interaction.response.send_message(
                            "❌ Gagal memuat genre.",
                            ephemeral=True
                        )
                        return
                else:
                    await interaction.response.send_message(
                        "❌ Database tidak tersedia.",
                        ephemeral=True
                    )
                    return
            else:
                # Default genre
                search_query = None

            # Defer response
            await interaction.response.defer()

            # Start unlimited play (includes confirmation if already active)
            await self.cog._start_unlimited_play_with_genre(self.ctx, search_query or genre_display, genre_display)

            # Disable the select
            select.disabled = True
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)

    # ==================== LYRICS COMMAND ====================
    @commands.command(name="lyrics", aliases=["l", "lyric"])
    async def lyrics_command(self, ctx: commands.Context):
        """
        Tampilkan lirik lagu yang sedang diputar.

        Usage: !lyrics atau !l
        """
        song = ytmusic_player.now_playing.get(ctx.guild.id)
        if not song:
            embed = self._create_embed(
                "❌ Tidak Ada Lagu",
                "Tidak ada lagu yang sedang diputar!",
                config.COLORS["error"]
            )
            return await ctx.send(embed=embed)

        # Show typing indicator
        async with ctx.typing():
            lyrics = await MusicControlView._fetch_lyrics_static(song.video_id, song.title, song.artist)

        if not lyrics:
            embed = self._create_embed(
                "❌ Tidak Ada Lyrics",
                "Lyrics tidak tersedia untuk lagu ini",
                config.COLORS["error"]
            )
            return await ctx.send(embed=embed)

        # Split lyrics if too long (Discord embed limit is 4096 chars)
        if len(lyrics) > 4000:
            lyrics = lyrics[:4000] + "\n\n... (lirik terpotong karena terlalu panjang)"

        embed = discord.Embed(
            title=f"📜 Lirik: {song.title}",
            description=f"**Artist:** {song.artist}\n\n{'─' * 40}\n\n{lyrics}",
            color=config.COLORS["music"]
        )

        await ctx.send(embed=embed)

    # ==================== ERROR HANDLER ====================
    @play.error
    @pause.error
    @resume.error
    @skip.error
    @stop.error
    @queue.error
    @nowplaying.error
    @volume.error
    @shuffle.error
    @loop.error
    @remove.error
    @clear_queue.error
    @search.error
    @random_play.error
    @lyrics_command.error
    async def music_error(self, ctx: commands.Context, error):
        """Handle music command errors."""
        if isinstance(error, commands.MissingRequiredArgument):
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
    # Reset all autoplay states on bot startup to ensure clean state
    print("[MUSIC] Resetting autoplay states on startup...")
    ytmusic_player.autoplay_mode.clear()
    ytmusic_player.buffered_songs.clear()
    ytmusic_player.transitioning.clear()
    ytmusic_player.unlimited_play_mode.clear()
    ytmusic_player.unlimited_play_genre.clear()
    print("[MUSIC] Autoplay states reset complete.")
    await bot.add_cog(Music(bot))
