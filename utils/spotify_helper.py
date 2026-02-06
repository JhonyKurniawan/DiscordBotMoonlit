"""
Spotify Helper Module
====================
Helper untuk menangani URL Spotify tanpa butuh API credentials.
Menggunakan oEmbed API dan layanan publik lainnya.
"""

import re
import asyncio
import json
from typing import Optional, List, Dict
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup


@dataclass
class SpotifyTrack:
    """Representasi track dari Spotify."""
    title: str
    artist: str
    album: str = ""
    duration_ms: int = 0
    track_id: str = ""
    url: str = ""
    thumbnail: Optional[str] = None

    @property
    def duration_str(self) -> str:
        """Convert duration_ms ke string format MM:SS atau HH:MM:SS."""
        seconds = self.duration_ms // 1000
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)

        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    def to_search_query(self) -> str:
        """Format untuk search di YouTube."""
        main_artist = self.artist.split(',')[0].strip()
        clean_title = self.title.split('(')[0].split('[')[0].strip()
        return f"{main_artist} - {clean_title}"


class SimpleSpotifyParser:
    """
    Simple parser untuk Spotify URLs tanpa butuh credentials.
    Menggunakan oEmbed API (public) dan spotifydown.com API.
    """

    SPOTIFY_PATTERNS = {
        'track': re.compile(r'https?://open\.spotify\.com/track/([a-zA-Z0-9]+)(?:\?.*)?'),
        'playlist': re.compile(r'https?://open\.spotify\.com/playlist/([a-zA-Z0-9]+)(?:\?.*)?'),
        'album': re.compile(r'https?://open\.spotify\.com/album/([a-zA-Z0-9]+)(?:\?.*)?'),
    }

    @classmethod
    def is_spotify_url(cls, url: str) -> bool:
        """Cek apakah URL adalah link Spotify."""
        return any(
            pattern.search(url)
            for pattern in cls.SPOTIFY_PATTERNS.values()
        )

    @classmethod
    def get_url_type(cls, url: str) -> Optional[str]:
        """Dapatkan tipe URL: 'track', 'playlist', atau 'album'."""
        for url_type, pattern in cls.SPOTIFY_PATTERNS.items():
            if pattern.search(url):
                return url_type
        return None

    @classmethod
    def extract_id(cls, url: str) -> Optional[str]:
        """Extract Spotify ID dari URL."""
        for pattern in cls.SPOTIFY_PATTERNS.values():
            match = pattern.search(url)
            if match:
                return match.group(1)
        return None

    async def get_track_info_from_oembed(self, track_url: str) -> Optional[Dict]:
        """
        Ambil track info dari Spotify oEmbed API (public, no auth).
        Return dict dengan 'title', 'artist', 'thumbnail'.
        """
        track_id = self.extract_id(track_url)
        if not track_id:
            return None

        try:
            oembed_url = f"https://open.spotify.com/oembed?url=https://open.spotify.com/track/{track_id}"

            # Gunakan requests di thread pool untuk menghindari SSL issues di aiohttp
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                lambda: requests.get(oembed_url, timeout=10).json()
            )

            if data:
                # Parse "Artist - Title" format dari Spotify oEmbed
                full_title = data.get('title', '')
                if ' - ' in full_title:
                    parts = full_title.split(' - ', 1)
                    artist = parts[0].strip()
                    title = parts[1].strip()
                else:
                    artist = "Unknown"
                    title = full_title

                return {
                    'title': title,
                    'artist': artist,
                    'thumbnail': data.get('thumbnail_url'),
                    'track_id': track_id,
                    'url': track_url
                }

        except Exception as e:
            print(f"Error fetching oEmbed: {e}")

        return None

    async def get_playlist_tracks_from_spotifydown(self, playlist_url: str) -> List[Dict]:
        """
        Ambil tracks dari playlist/album menggunakan multiple methods:
        1. Spotify API (butuh token)
        2. spotifydown.com API
        3. Web scraping (fallback)
        """
        playlist_id = self.extract_id(playlist_url)
        if not playlist_id:
            return []

        url_type = self.get_url_type(playlist_url)

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        # Method 1: Try spotifydown.com API
        if url_type == 'playlist':
            api_url = f"https://api.spotifydown.com/metadata/playlist/{playlist_id}"
        elif url_type == 'album':
            api_url = f"https://api.spotifydown.com/metadata/album/{playlist_id}"
        else:
            return []

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(api_url, headers=headers, timeout=30)
            )

            if response.status_code == 200:
                data = response.json()
                tracks = self._parse_playlist_response(data, url_type)
                if tracks:
                    print(f"Loaded {len(tracks)} tracks from spotifydown API")
                    return tracks
        except Exception as e:
            print(f"spotifydown API failed: {e}")

        # Method 2: Web scraping fallback
        print("Trying web scraping fallback...")
        return await self._scrape_playlist_tracks(playlist_url, url_type)

    async def _scrape_playlist_tracks(self, playlist_url: str, url_type: str) -> List[Dict]:
        """
        Scraping playlist/album tracks dari Spotify web page menggunakan Playwright.
        Fallback method jika API tidak available.
        """
        try:
            from playwright.async_api import async_playwright

            playlist_id = self.extract_id(playlist_url)
            if not playlist_id:
                return []

            # Gunakan embed URL untuk loading lebih cepat
            embed_url = f"https://open.spotify.com/embed/playlist/{playlist_id}"

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                print(f"Loading Spotify {url_type} with Playwright...")
                await page.goto(embed_url)

                # Wait for playlist to load
                await page.wait_for_timeout(8000)

                # Get track data from the page
                # Spotify embed menyimpan data dalam script
                tracks_data = await page.evaluate('''() => {
                    const tracks = [];

                    // Method 1: Cari data di Spotify object
                    if (window.Spotify) {
                        const entity = window.Spotify.Entity;
                        if (entity && entity.items) {
                            entity.items.forEach(item => {
                                if (item.track) {
                                    tracks.push({
                                        title: item.track.name || item.track.title,
                                        artist: item.track.artists || item.track.artistName,
                                        album: item.track.album && item.track.album.name,
                                        duration: item.track.duration
                                    });
                                }
                            });
                        }
                    }

                    // Method 2: Parse dari DOM elements
                    if (tracks.length === 0) {
                        const trackElements = document.querySelectorAll('[data-testid="tracklist-row"]');
                        trackElements.forEach(el => {
                            const titleEl = el.querySelector('[data-testid="track-title"]');
                            const artistEl = el.querySelector('[data-testid="track-artist"]');
                            if (titleEl && artistEl) {
                                tracks.push({
                                    title: titleEl.textContent,
                                    artist: artistEl.textContent
                                });
                            }
                        });
                    }

                    // Method 3: Parse dari semua teks di page
                    if (tracks.length === 0) {
                        const bodyText = document.body.textContent || '';
                        const lines = bodyText.split('\\n');

                        // Cari pattern "Artist - Title" atau "Title - Artist"
                        lines.forEach(line => {
                            line = line.trim();
                            if (line.includes(' - ') && line.length > 10 && line.length < 150) {
                                const parts = line.split(' - ');
                                if (parts.length >= 2) {
                                    // Cek apakah ini track (ada angka duration di akhir)
                                    const lastPart = parts[parts.length - 1].trim();
                                    if (/^\\d+:\\d+$/.test(lastPart) || lastPart.length < 50) {
                                        tracks.push({
                                            title: parts.slice(1).join(' - ').trim(),
                                            artist: parts[0].trim()
                                        });
                                    }
                                }
                            }
                        });
                    }

                    return tracks;
                }''')

                await browser.close()

                if tracks_data:
                    print(f"Found {len(tracks_data)} tracks via Playwright")

                    # Convert ke format yang diharapkan
                    tracks = []
                    seen = set()
                    for track in tracks_data:
                        title = track.get('title', '').strip()
                        artist = track.get('artist', '').strip()

                        if title and artist and (title, artist) not in seen:
                            seen.add((title, artist))
                            tracks.append({
                                'title': title,
                                'artist': artist,
                                'album': track.get('album', ''),
                                'duration_ms': 0,
                                'duration_text': track.get('duration', ''),
                                'track_id': '',
                                'thumbnail': None
                            })

                    return tracks[:100]  # Max 100 tracks

        except ImportError:
            print("Playwright not installed, skipping JS rendering")
        except Exception as e:
            print(f"Error with Playwright scraping: {e}")

        # Fallback ke static HTML parsing
        return await self._scrape_static_html(playlist_url, url_type)

    async def _scrape_static_html(self, playlist_url: str, _url_type: str) -> List[Dict]:
        """Fallback: Parse static HTML (tanpa JavaScript rendering)."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(playlist_url, headers=headers, timeout=30)
            )

            if response.status_code != 200:
                print(f"Failed to fetch page: {response.status_code}")
                return []

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find script tag with Spotify data
            scripts = soup.find_all('script', {'id': '__NEXT_DATA__'})

            for script in scripts:
                try:
                    data = json.loads(script.string)
                    tracks = self._extract_tracks_from_json(data, _url_type)
                    if tracks:
                        print(f"Loaded {len(tracks)} tracks from static HTML")
                        return tracks
                except Exception as e:
                    print(f"Error parsing script data: {e}")
                    continue

            print("Could not find track data in static HTML")
            return []

        except Exception as e:
            print(f"Error in static HTML fallback: {e}")
            return []

    def _extract_tracks_from_json(self, data: Dict, _url_type: str) -> List[Dict]:
        """Extract tracks dari Spotify JSON data dengan recursive search."""
        tracks = []

        def find_tracks_in_dict(obj, depth=0):
            """Recursive search untuk tracks dalam dict."""
            if depth > 20:  # Limit depth untuk prevent infinite loop
                return

            if isinstance(obj, dict):
                # Cek jika ini adalah track object
                if 'id' in obj and 'name' in obj:
                    # Pastikan ini track, bukan artist atau album
                    if 'artists' in obj or 'duration_ms' in obj:
                        track_id = obj.get('id', '')
                        name = obj.get('name', '')
                        # Skip jika ini artist type
                        if obj.get('type') == 'artist':
                            return

                        if track_id and name:
                            # Get artist name
                            artist = 'Unknown'
                            if 'artists' in obj and isinstance(obj['artists'], list) and len(obj['artists']) > 0:
                                artists_list = obj['artists']
                                if isinstance(artists_list[0], dict):
                                    artist = artists_list[0].get('name', 'Unknown')
                                elif isinstance(artists_list[0], str):
                                    artist = artists_list[0]

                            if artist != 'Unknown':  # Valid track
                                # Cek duplicate
                                if not any(t.get('track_id') == track_id for t in tracks):
                                    tracks.append({
                                        'title': name,
                                        'artist': artist,
                                        'album': obj.get('album', {}).get('name', '') if isinstance(obj.get('album'), dict) else '',
                                        'duration_ms': obj.get('duration_ms', 0),
                                        'duration_text': '',
                                        'track_id': track_id,
                                        'thumbnail': None
                                    })

                # Recurse ke nested dicts
                for value in obj.values():
                    find_tracks_in_dict(value, depth + 1)

            elif isinstance(obj, list):
                for item in obj:
                    find_tracks_in_dict(item, depth + 1)

        try:
            find_tracks_in_dict(data)
            return tracks[:100]  # Max 100 tracks

        except Exception as e:
            print(f"Error extracting tracks from JSON: {e}")
            return []

    def _parse_playlist_response(self, data: Dict, _url_type: str = None) -> List[Dict]:
        """Parse playlist/album response from various APIs."""
        tracks = []

        try:
            # Try Spotify API format
            if 'tracks' in data and 'items' in data['tracks']:
                track_list = data['tracks']['items']
                for item in track_list:
                    track = item.get('track')
                    if track and not track.get('is_local'):
                        tracks.append(self._parse_track_data(track))

            # Try spotifydown format
            elif 'tracks' in data or 'trackList' in data:
                track_list = data.get('tracks', data.get('trackList', []))
                for item in track_list:
                    if isinstance(item, dict):
                        track_title = item.get('title', item.get('name', ''))
                        artist_name = item.get('artist', item.get('artists', 'Unknown'))

                        if isinstance(artist_name, list):
                            artist_name = ', '.join([
                                a.get('name', str(a)) if isinstance(a, dict) else str(a)
                                for a in artist_name
                            ])

                        duration = item.get('duration', item.get('durationText', ''))
                        duration_ms = 0
                        if duration and isinstance(duration, str):
                            parts = duration.split(':')
                            if len(parts) == 2:
                                duration_ms = (int(parts[0]) * 60 + int(parts[1])) * 1000
                            elif len(parts) == 3:
                                duration_ms = (int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])) * 1000

                        tracks.append({
                            'title': track_title,
                            'artist': artist_name,
                            'album': data.get('title', data.get('name', '')),
                            'duration_ms': duration_ms,
                            'duration_text': duration,
                            'track_id': item.get('id', ''),
                            'thumbnail': item.get('cover', item.get('image', item.get('thumbnail')))
                        })

        except Exception as e:
            print(f"Error parsing playlist response: {e}")

        return tracks

    def _parse_track_data(self, track: Dict, _url_type: str = None) -> Dict:
        """Parse track data from Spotify API format."""
        artists = track.get('artists', [])
        artist_name = artists[0].get('name', 'Unknown') if artists else 'Unknown'

        duration_ms = track.get('duration_ms', 0)

        thumbnail = None
        if track.get('album') and track['album'].get('images'):
            images = track['album']['images']
            thumbnail = images[0].get('url') if images else None

        return {
            'title': track.get('name', ''),
            'artist': artist_name,
            'album': track.get('album', {}).get('name', ''),
            'duration_ms': duration_ms,
            'duration_text': '',
            'track_id': track.get('id', ''),
            'thumbnail': thumbnail
        }

    async def get_playlist_tracks_basic(self, playlist_url: str) -> List[Dict]:
        """Wrapper method untuk compatibility."""
        return await self.get_playlist_tracks_from_spotifydown(playlist_url)

    async def get_album_tracks_basic(self, album_url: str) -> List[Dict]:
        """Wrapper method untuk compatibility - album uses same API."""
        return await self.get_playlist_tracks_from_spotifydown(album_url)


# Singleton instance
spotify_parser = SimpleSpotifyParser()


def is_spotify_url(url: str) -> bool:
    """Quick check jika URL adalah Spotify URL."""
    return SimpleSpotifyParser.is_spotify_url(url)


def get_spotify_url_type(url: str) -> Optional[str]:
    """Dapatkan tipe Spotify URL."""
    return SimpleSpotifyParser.get_url_type(url)


def format_search_query(title: str, artist: str) -> str:
    """Format query untuk search di YouTube."""
    main_artist = artist.split(',')[0].strip()
    # Clean title dari fit/version info untuk search lebih baik
    clean_title = title.split('(')[0].split('[')[0].strip()
    return f"{main_artist} - {clean_title}"
