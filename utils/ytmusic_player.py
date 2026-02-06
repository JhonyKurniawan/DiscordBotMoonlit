"""
YouTube Music Player Utility
============================
Wrapper untuk ytmusicapi dan yt-dlp untuk streaming audio.
Juga mendukung Spotify URLs via spotdl.
"""

import asyncio
import discord
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from ytmusicapi import YTMusic
import yt_dlp

import re

# Import Spotify helper
from utils.spotify_helper import (
    is_spotify_url,
    get_spotify_url_type,
    spotify_parser,
    format_search_query
)

# YT-DLP Options untuk audio extraction
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

# FFmpeg Options untuk audio streaming
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}


@dataclass
class Song:
    """Representasi sebuah lagu dalam queue."""
    title: str
    artist: str
    url: str
    video_id: str
    thumbnail: Optional[str] = None
    duration: Optional[str] = None
    requester: Optional[discord.Member] = None

    @property
    def youtube_url(self) -> str:
        """Return YouTube URL dari video ID."""
        return f"https://www.youtube.com/watch?v={self.video_id}"


@dataclass
class MusicQueue:
    """Queue system untuk music player."""
    songs: List[Song] = field(default_factory=list)
    current_index: int = 0
    loop: bool = False
    loop_single: bool = False

    def add(self, song: Song) -> int:
        """Tambah lagu ke queue. Return posisi dalam queue."""
        self.songs.append(song)
        # Return actual position (upcoming count + 1)
        return len(self.songs) - self.current_index

    def insert_at_front(self, song: Song) -> int:
        """Insert lagu di posisi depan (setelah lagu saat ini). Return posisi."""
        # Insert at position 1 (right after current song at index 0)
        insert_pos = 1
        self.songs.insert(insert_pos, song)
        return 1  # Always returns position 1 (next to play)

    def next(self) -> Optional[Song]:
        """Ambil lagu berikutnya dan hapus lagu yang sudah selesai."""
        if self.loop_single and self.songs:
            return self.songs[0] if self.songs else None

        # Hapus lagu yang sudah selesai (lagu saat ini di index 0)
        if self.songs and self.current_index >= 0:
            # Remove the song that just finished (index 0)
            self.songs.pop(0)

        # Reset current_index to 0 (next song becomes current)
        self.current_index = 0

        # Check if queue is empty
        if not self.songs:
            return None

        # Handle loop all
        if self.loop and self.songs:
            return self.songs[0]

        # Return next song (now at index 0)
        return self.songs[0] if self.songs else None

    @property
    def current_song(self) -> Optional[Song]:
        """Ambil lagu yang sedang diputar."""
        if self.songs and 0 <= self.current_index < len(self.songs):
            return self.songs[self.current_index]
        return None

    def clear(self):
        """Kosongkan queue."""
        self.songs.clear()
        self.current_index = 0

    def remove(self, index: int) -> Optional[Song]:
        """Hapus lagu dari queue berdasarkan index."""
        # Adjust index for current song (index 0 is current, can't remove)
        actual_index = self.current_index + index
        if 0 <= actual_index < len(self.songs):
            song = self.songs.pop(actual_index)
            return song
        return None

    def shuffle(self):
        """Acak lagu dalam queue (kecuali yang sedang diputar)."""
        import random
        if len(self.songs) > 1:
            # Keep current song (index 0), shuffle the rest
            current = self.songs[0] if self.songs else None
            remaining = self.songs[1:] if len(self.songs) > 1 else []
            random.shuffle(remaining)
            self.songs = [current] + remaining if current else remaining

    def __len__(self) -> int:
        return len(self.songs)

    @property
    def upcoming(self) -> List[Song]:
        """Return daftar lagu yang akan diputar."""
        # Songs from index 1 onwards (index 0 is current)
        return self.songs[1:] if len(self.songs) > 1 else []


class YTMusicPlayer:
    """Player untuk streaming musik dari YouTube Music."""

    def __init__(self):
        self.ytmusic = YTMusic()
        self.ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)
        self.queues: Dict[int, MusicQueue] = {}  # guild_id -> MusicQueue
        self.volumes: Dict[int, float] = {}  # guild_id -> volume (0.0 - 1.0)
        self.now_playing: Dict[int, Song] = {}  # guild_id -> current song
        # Unlimited play state
        self.unlimited_play_mode: Dict[int, bool] = {}  # guild_id -> is_active
        self.unlimited_play_genre: Dict[int, str] = {}  # guild_id -> genre
        # Buffer for unlimited play (preloaded next song)
        self.buffered_songs: Dict[int, Song] = {}  # guild_id -> buffered song
        # Autoplay state (plays similar songs automatically)
        self.autoplay_mode: Dict[int, bool] = {}  # guild_id -> is_active
        # Transitioning state to prevent race conditions during song changes
        self.transitioning: Dict[int, bool] = {}  # guild_id -> is_transitioning

    def get_queue(self, guild_id: int) -> MusicQueue:
        """Ambil atau buat queue untuk guild."""
        if guild_id not in self.queues:
            self.queues[guild_id] = MusicQueue()
        return self.queues[guild_id]

    def get_volume(self, guild_id: int) -> float:
        """Ambil volume untuk guild (default 0.5 = 50%)."""
        return self.volumes.get(guild_id, 1.0)

    def set_volume(self, guild_id: int, volume: float):
        """Set volume untuk guild (0.0 - 1.0)."""
        self.volumes[guild_id] = max(0.0, min(1.0, volume))

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Cari lagu di YouTube Music.
        
        Args:
            query: Kata kunci pencarian
            limit: Jumlah hasil maksimal
            
        Returns:
            List hasil pencarian
        """
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: self.ytmusic.search(query, filter="songs", limit=limit)
        )
        return results

    def _extract_playlist_id(self, url: str) -> Optional[str]:
        """Extract playlist ID dari URL."""
        # Pattern untuk YouTube Music playlist
        patterns = [
            r'[?&]list=([a-zA-Z0-9_-]+)',
            r'playlist\?list=([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def _is_playlist_url(self, url: str) -> bool:
        """Check apakah URL adalah playlist."""
        return 'list=' in url and 'watch?v=' not in url

    def _is_spotify_url(self, url: str) -> bool:
        """Check apakah URL adalah link Spotify."""
        return is_spotify_url(url)

    def _get_spotify_url_type(self, url: str) -> Optional[str]:
        """Dapatkan tipe URL Spotify: 'track', 'playlist', atau 'album'."""
        return get_spotify_url_type(url)

    async def get_playlist_songs(self, playlist_url: str, requester: discord.Member = None) -> List[Song]:
        """
        Ambil semua lagu dari playlist YouTube Music.
        
        Args:
            playlist_url: URL playlist
            requester: Member yang request
            
        Returns:
            List of Song objects
        """
        songs = []
        
        try:
            playlist_id = self._extract_playlist_id(playlist_url)
            
            if not playlist_id:
                print(f"Could not extract playlist ID from: {playlist_url}")
                return songs
            
            # Get playlist info from ytmusicapi
            loop = asyncio.get_event_loop()
            playlist_data = await loop.run_in_executor(
                None,
                lambda: self.ytmusic.get_playlist(playlist_id, limit=100)
            )
            
            if not playlist_data:
                print(f"Could not get playlist data for: {playlist_id}")
                return songs
            
            tracks = playlist_data.get('tracks', [])
            
            for track in tracks:
                video_id = track.get('videoId')
                if not video_id:
                    continue
                
                # Extract artist
                artists = track.get('artists', [])
                artist_name = artists[0].get('name', 'Unknown') if artists else 'Unknown'
                
                # Extract thumbnail
                thumbnails = track.get('thumbnails', [])
                thumbnail = thumbnails[-1].get('url') if thumbnails else None
                
                # Extract duration
                duration = track.get('duration', 'Unknown')
                
                song = Song(
                    title=track.get('title', 'Unknown'),
                    artist=artist_name,
                    url='',  # Will be fetched when playing
                    video_id=video_id,
                    thumbnail=thumbnail,
                    duration=duration,
                    requester=requester
                )
                songs.append(song)
                
            print(f"Loaded {len(songs)} songs from playlist")
            
        except Exception as e:
            print(f"Error getting playlist: {e}")

        return songs

    async def _get_spotify_track(self, track_url: str, requester: discord.Member = None) -> Optional[Song]:
        """
        Ambil info lagu dari Spotify URL dan cari di YouTube.

        Args:
            track_url: URL track Spotify
            requester: Member yang request lagu

        Returns:
            Song object atau None jika tidak ditemukan
        """
        try:
            # Get track info dari Spotify oEmbed
            track_info = await spotify_parser.get_track_info_from_oembed(track_url)

            if not track_info:
                print(f"Could not get Spotify track info from: {track_url}")
                return None

            # Format search query untuk YouTube
            search_query = format_search_query(
                track_info['title'],
                track_info['artist']
            )

            # Search di YouTube Music
            results = await self.search(search_query, limit=1)

            if not results:
                # Fallback: search dengan judul saja
                results = await self.search(track_info['title'], limit=1)

            if not results:
                print(f"No YouTube results found for: {search_query}")
                return None

            result = results[0]
            video_id = result.get('videoId', '')

            # Extract artist dari YouTube result
            artists = result.get('artists', [])
            artist_name = artists[0].get('name', 'Unknown') if artists else 'Unknown'

            # Extract thumbnail
            thumbnails = result.get('thumbnails', [])
            thumbnail = thumbnails[-1].get('url') if thumbnails else None
            # Prioritize Spotify thumbnail jika available
            if track_info.get('thumbnail'):
                thumbnail = track_info['thumbnail']

            # Extract duration
            duration = result.get('duration', 'Unknown')

            return Song(
                title=track_info['title'],  # Gunakan judul dari Spotify (lebih clean)
                artist=track_info['artist'],  # Gunakan artist dari Spotify
                url='',  # Will be fetched when playing
                video_id=video_id,
                thumbnail=thumbnail,
                duration=duration,
                requester=requester
            )

        except Exception as e:
            print(f"Error getting Spotify track: {e}")

        return None

    async def get_spotify_playlist_songs(self, playlist_url: str, requester: discord.Member = None) -> List[Song]:
        """
        Ambil semua lagu dari Spotify playlist/album dan cari di YouTube.

        Args:
            playlist_url: URL playlist/album Spotify
            requester: Member yang request

        Returns:
            List of Song objects
        """
        songs = []
        spotify_type = self._get_spotify_url_type(playlist_url)

        if spotify_type != 'playlist' and spotify_type != 'album':
            print(f"Not a Spotify playlist/album URL: {playlist_url}")
            return songs

        try:
            # Get tracks dari Spotify
            if spotify_type == 'playlist':
                tracks_info = await spotify_parser.get_playlist_tracks_basic(playlist_url)
            else:  # album
                tracks_info = await spotify_parser.get_album_tracks_basic(playlist_url)

            if not tracks_info:
                print(f"Could not get tracks from Spotify: {playlist_url}")
                return songs

            # Convert setiap track ke Song objects dengan mencari di YouTube
            for track_info in tracks_info:
                try:
                    # Format search query
                    search_query = format_search_query(
                        track_info['title'],
                        track_info['artist']
                    )

                    # Search di YouTube Music
                    results = await self.search(search_query, limit=1)

                    if not results:
                        # Skip jika tidak ditemukan
                        print(f"Could not find YouTube match for: {search_query}")
                        continue

                    result = results[0]
                    video_id = result.get('videoId', '')

                    # Extract thumbnail
                    thumbnails = result.get('thumbnails', [])
                    thumbnail = thumbnails[-1].get('url') if thumbnails else None
                    # Prioritize Spotify thumbnail
                    if track_info.get('thumbnail'):
                        thumbnail = track_info['thumbnail']

                    # Format duration
                    duration = 'Unknown'
                    if track_info.get('duration_ms'):
                        seconds = track_info['duration_ms'] // 1000
                        mins, secs = divmod(seconds, 60)
                        duration = f"{mins}:{secs:02d}"
                    elif result.get('duration'):
                        duration = result['duration']

                    song = Song(
                        title=track_info['title'],
                        artist=track_info['artist'],
                        url='',  # Will be fetched when playing
                        video_id=video_id,
                        thumbnail=thumbnail,
                        duration=duration,
                        requester=requester
                    )
                    songs.append(song)

                except Exception as e:
                    print(f"Error processing Spotify track: {e}")
                    continue

            print(f"Loaded {len(songs)} songs from Spotify {spotify_type}")

        except Exception as e:
            print(f"Error getting Spotify playlist/album: {e}")

        return songs

    async def get_song_info(self, query: str, requester: discord.Member = None) -> Optional[Song]:
        """
        Cari dan ambil info lagu dari query.
        Support YouTube Music dan Spotify URLs.

        Args:
            query: Kata kunci atau URL (YouTube/Spotify)
            requester: Member yang request lagu

        Returns:
            Song object atau None jika tidak ditemukan
        """
        try:
            # Cek apakah query adalah Spotify URL
            if self._is_spotify_url(query):
                spotify_type = self._get_spotify_url_type(query)

                if spotify_type == 'track':
                    return await self._get_spotify_track(query, requester)
                elif spotify_type in ('playlist', 'album'):
                    # Playlist/album handled separately in get_spotify_playlist_songs
                    return None

            # Cek apakah query adalah YouTube URL
            if "youtube.com" in query or "youtu.be" in query or "music.youtube.com" in query:
                # Extract video ID dari URL
                loop = asyncio.get_event_loop()
                info = await loop.run_in_executor(
                    None,
                    lambda: self.ytdl.extract_info(query, download=False)
                )
                
                if info:
                    return Song(
                        title=info.get('title', 'Unknown'),
                        artist=info.get('uploader', 'Unknown'),
                        url=info.get('url', query),
                        video_id=info.get('id', ''),
                        thumbnail=info.get('thumbnail'),
                        duration=self._format_duration(info.get('duration', 0)),
                        requester=requester
                    )
            else:
                # Search di YouTube Music
                results = await self.search(query, limit=1)
                
                if results:
                    result = results[0]
                    video_id = result.get('videoId', '')
                    
                    # Get stream URL menggunakan yt-dlp
                    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
                    loop = asyncio.get_event_loop()
                    info = await loop.run_in_executor(
                        None,
                        lambda: self.ytdl.extract_info(youtube_url, download=False)
                    )
                    
                    # Extract artist name
                    artists = result.get('artists', [])
                    artist_name = artists[0].get('name', 'Unknown') if artists else 'Unknown'
                    
                    # Extract duration
                    duration = result.get('duration', '')
                    if not duration and info:
                        duration = self._format_duration(info.get('duration', 0))
                    
                    # Extract thumbnail
                    thumbnails = result.get('thumbnails', [])
                    thumbnail = thumbnails[-1].get('url') if thumbnails else None
                    
                    return Song(
                        title=result.get('title', 'Unknown'),
                        artist=artist_name,
                        url=info.get('url', youtube_url) if info else youtube_url,
                        video_id=video_id,
                        thumbnail=thumbnail,
                        duration=duration,
                        requester=requester
                    )
                    
        except Exception as e:
            print(f"Error getting song info: {e}")
            
        return None

    async def get_stream_url(self, video_id: str) -> Optional[str]:
        """
        Ambil stream URL dari video ID.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Stream URL atau None
        """
        try:
            youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None,
                lambda: self.ytdl.extract_info(youtube_url, download=False)
            )
            
            if info:
                return info.get('url')
                
        except Exception as e:
            print(f"Error getting stream URL: {e}")
            
        return None

    def create_audio_source(self, url: str, volume: float = 0.5) -> discord.PCMVolumeTransformer:
        """
        Buat audio source dari URL.
        
        Args:
            url: Stream URL
            volume: Volume level (0.0 - 1.0)
            
        Returns:
            PCMVolumeTransformer audio source
        """
        source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
        return discord.PCMVolumeTransformer(source, volume=volume)

    def _format_duration(self, seconds: int) -> str:
        """Format durasi dari detik ke MM:SS atau HH:MM:SS."""
        if not seconds:
            return "Unknown"

        hours, remainder = divmod(int(seconds), 3600)
        minutes, secs = divmod(remainder, 60)

        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    async def get_random_songs_by_genre(self, genre: str, count: int, requester: discord.Member = None) -> List[Song]:
        """
        Dapatkan lagu random dari genre tertentu.

        Args:
            genre: Kategori genre (pop, rock, hip-hop, edm, jazz, classical, k-pop, rnb, country, lofi, indie)
                   Atau custom search query untuk genre user-defined
            count: Jumlah lagu yang akan diambil
            requester: Member yang request lagu

        Returns:
            List of Song objects
        """
        # Genre search queries
        GENRE_QUERIES = {
            "pop": "top pop songs 2024",
            "rock": "best rock songs classic",
            "hip-hop": "hip hop rap playlist",
            "edm": "edm electronic dance music",
            "jazz": "jazz classics playlist",
            "classical": "classical music mozart beethoven",
            "k-pop": "kpop playlist bts blackpink",
            "rnb": "rnb soul music playlist",
            "country": "country music hits",
            "lofi": "lofi hip hop beats",
            "indie": "indie folk playlist",
        }

        # Get query from predefined genres or use genre as custom search query
        query = GENRE_QUERIES.get(genre.lower())
        if not query:
            # Use the genre parameter directly as search query (for custom genres)
            query = genre

        try:
            # Search dengan limit lebih banyak untuk variasi
            results = await self.search(query, limit=25)

            if not results:
                return []

            # Randomly select dari hasil
            import random
            selected = random.sample(results, min(count, len(results)))

            # Convert ke Song objects
            songs = []
            for result in selected:
                video_id = result.get('videoId')
                if not video_id:
                    continue

                # Extract artist
                artists = result.get('artists', [])
                artist = artists[0].get('name', 'Unknown') if artists else 'Unknown'

                # Extract thumbnail
                thumbnails = result.get('thumbnails', [])
                thumbnail = thumbnails[-1].get('url') if thumbnails else None

                song = Song(
                    title=result.get('title', 'Unknown'),
                    artist=artist,
                    url='',  # Will be fetched when playing
                    video_id=video_id,
                    thumbnail=thumbnail,
                    duration=result.get('duration', 'Unknown'),
                    requester=requester
                )
                songs.append(song)

            return songs

        except Exception as e:
            print(f"Error getting random songs by genre: {e}")
            return []

    def cleanup(self, guild_id: int):
        """Bersihkan data untuk guild."""
        if guild_id in self.queues:
            del self.queues[guild_id]
        if guild_id in self.now_playing:
            del self.now_playing[guild_id]
        self.clear_unlimited_play(guild_id)
        # Also clear autoplay mode and buffer
        self.autoplay_mode.pop(guild_id, None)
        self.clear_buffer(guild_id)
        # Clear transitioning state
        self.set_transitioning(guild_id, False)

    def set_unlimited_play(self, guild_id: int, genre: str):
        """Enable unlimited play mode."""
        self.unlimited_play_mode[guild_id] = True
        self.unlimited_play_genre[guild_id] = genre

    def clear_unlimited_play(self, guild_id: int):
        """Disable unlimited play mode."""
        self.unlimited_play_mode.pop(guild_id, None)
        self.unlimited_play_genre.pop(guild_id, None)
        self.clear_buffer(guild_id)  # Also clear buffer

    def is_unlimited_play_active(self, guild_id: int) -> bool:
        """Check if unlimited play is active."""
        return self.unlimited_play_mode.get(guild_id, False)

    def get_unlimited_genre(self, guild_id: int) -> Optional[str]:
        """Get unlimited play genre."""
        return self.unlimited_play_genre.get(guild_id)

    # ==================== AUTOPAY METHODS ====================
    def set_autoplay(self, guild_id: int, enabled: bool = True):
        """Enable or disable autoplay mode."""
        self.autoplay_mode[guild_id] = enabled

    def is_autoplay_active(self, guild_id: int) -> bool:
        """Check if autoplay is active."""
        return self.autoplay_mode.get(guild_id, False)

    def toggle_autoplay(self, guild_id: int) -> bool:
        """Toggle autoplay mode and return new state."""
        current = self.is_autoplay_active(guild_id)
        self.set_autoplay(guild_id, not current)
        return not current

    async def get_similar_songs(self, current_song: 'Song', count: int = 1) -> List[Song]:
        """
        Get similar songs based on current song.
        Uses multiple search strategies to find similar songs.
        """
        try:
            # Clean artist name for better search
            artist_clean = current_song.artist.strip()

            # Try multiple search queries in order of preference
            search_queries = [
                f"{artist_clean} songs",           # "The 1975 songs"
                f"{artist_clean} best songs",     # "The 1975 best songs"
                f"songs like {current_song.title}",  # "songs like Somebody Else"
                f"similar to {artist_clean}",     # "similar to The 1975"
                artist_clean,                     # Just artist name
            ]

            results = []
            for query in search_queries:
                print(f"[AUTOPLAY SEARCH] Trying query: '{query}'")
                results = await self.search(query, limit=count + 5)
                if results:
                    print(f"[AUTOPLAY SEARCH] Found {len(results)} results for: '{query}'")
                    break

            if not results:
                print(f"[AUTOPLAY SEARCH] No results found for any query")
                return []

            songs = []
            for result in results[:count + 10]:  # Check more results to find unique ones
                # Extract video ID and title
                video_id = result.get('videoId')
                if video_id:
                    title = result.get('title', 'Unknown')
                    artists = result.get('artists', [])
                    artist_name = artists[0].get('name', 'Unknown') if artists else 'Unknown'

                    # Extract thumbnail
                    thumbnails = result.get('thumbnails', [])
                    thumbnail = thumbnails[-1].get('url') if thumbnails else None

                    # Extract duration (string format like "3:45")
                    duration = result.get('duration', 'Unknown')

                    song = Song(
                        title=title,
                        artist=artist_name,
                        url='',  # Will be fetched when playing
                        video_id=video_id,
                        thumbnail=thumbnail,
                        duration=duration
                    )
                    # Skip the same song
                    if song.video_id != current_song.video_id and len(songs) < count:
                        songs.append(song)

            print(f"[AUTOPLAY SEARCH] Returning {len(songs)} similar songs")
            return songs
        except Exception as e:
            print(f"Error getting similar songs: {e}")
            return []

    # ==================== BUFFER METHODS ====================
    def set_buffer(self, guild_id: int, song: Song):
        """Set buffered song for unlimited play."""
        self.buffered_songs[guild_id] = song

    def get_buffer(self, guild_id: int) -> Optional[Song]:
        """Get buffered song."""
        return self.buffered_songs.get(guild_id)

    def clear_buffer(self, guild_id: int):
        """Clear buffered song."""
        self.buffered_songs.pop(guild_id, None)

    def has_buffer(self, guild_id: int) -> bool:
        """Check if buffer exists."""
        return guild_id in self.buffered_songs

    # ==================== TRANSITION STATE METHODS ====================
    def set_transitioning(self, guild_id: int, is_transitioning: bool):
        """Set transitioning state for a guild."""
        if is_transitioning:
            self.transitioning[guild_id] = True
        else:
            self.transitioning.pop(guild_id, None)

    def is_transitioning(self, guild_id: int) -> bool:
        """Check if guild is in transitioning state."""
        return self.transitioning.get(guild_id, False)


# Global instance
ytmusic_player = YTMusicPlayer()
