"""
Chatbot Cog
===========
AI chatbot menggunakan Groq API.
"""

import discord
from discord.ext import commands
import aiohttp
import re
from typing import Optional, List, Dict
import config
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dashboard.backend import database as db
    HAS_DATABASE = True
    print("✅ Chatbot: Database module loaded")
except Exception as e:
    HAS_DATABASE = False
    print(f"❌ Chatbot: Database import failed: {e}")


class Chatbot(commands.Cog):
    """AI Chatbot menggunakan Groq API."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api_base = "https://api.groq.com/openai/v1"
        self.session: Optional[aiohttp.ClientSession] = None

    def _create_embed(self, title: str, description: str, color: int) -> discord.Embed:
        """Helper untuk membuat embed."""
        return discord.Embed(
            title=title,
            description=description,
            color=color
        )

    def _get_settings(self, guild_id: int) -> dict:
        """Dapatkan chatbot settings untuk guild."""
        if HAS_DATABASE:
            settings = db.get_chatbot_settings(guild_id)
            if settings:
                system_prompt_raw = settings.get('system_prompt', '')
                system_prompt = system_prompt_raw if system_prompt_raw and system_prompt_raw.strip() else ''
                return {
                    'enabled': settings.get('enabled', 0) == 1,
                    'enabled_channels': settings.get('enabled_channels', []),
                    'system_prompt': system_prompt,
                    'api_key': settings.get('api_key') or config.GROQ_API_KEY,
                    'max_history': settings.get('max_history', 10),
                    'temperature': settings.get('temperature', 0.7),
                    'model_name': settings.get('model_name') or settings.get('model', getattr(config, 'GROQ_MODEL', 'llama-3.3-70b-versatile'))
                }
        return {
            'enabled': False,
            'enabled_channels': [],
            'system_prompt': '',
            'api_key': config.GROQ_API_KEY,
            'max_history': 10,
            'temperature': 0.7,
            'model_name': getattr(config, 'GROQ_MODEL', 'llama-3.3-70b-versatile')
        }

    def _is_enabled_channel(self, channel_id: int, settings: dict) -> bool:
        """Cek apakah channel adalah enabled channel."""
        enabled_channels = settings.get('enabled_channels', [])
        # Convert to strings for comparison (handles both int and string from DB)
        enabled_channels_str = [str(ch) for ch in enabled_channels]
        return str(channel_id) in enabled_channels_str

    def _clean_response(self, response: str) -> str:
        """Bersihkan response dari thinking tags dan batasi ke 1900 karakter."""
        if not response:
            return ""

        # Hapus thinking tags dan isinya
        # Hapus <think>...</think> dengan semua isi di dalamnya
        response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE)
        # Hapus sisa tags jika ada
        response = re.sub(r'<think>.*', '', response, flags=re.DOTALL | re.IGNORECASE)
        response = re.sub(r'.*</think>', '', response, flags=re.DOTALL | re.IGNORECASE)

        # Trim whitespace
        return response.strip()

    def _split_message(self, text: str, max_length: int = 3900) -> List[str]:
        """Split pesan panjang menjadi beberapa bagian dengan logika pemotongan yang baik.

        Discord limit: 4000 karakter. Kita pakai 3900 untuk aman.
        Mencoba memotong di baris baru agar teks tidak terpotong di tengah kalimat.
        """
        if len(text) <= max_length:
            return [text]

        parts = []
        remaining = text

        while remaining:
            if len(remaining) <= max_length:
                parts.append(remaining)
                break

            # Cari baris baru terakhir sebelum batas max_length
            # Ambil teks sampai max_length + 100 untuk mencari titik potong yang baik
            chunk = remaining[:max_length + 100]

            # Prioritas 1: Cari double newline (paragraf baru)
            split_pos = chunk.rfind('\n\n', max_length - 500, max_length + 100)

            # Prioritas 2: Cari single newline
            if split_pos == -1:
                split_pos = chunk.rfind('\n', max_length - 200, max_length + 100)

            # Prioritas 3: Cari titik atau spasi
            if split_pos == -1:
                split_pos = chunk.rfind('. ', max_length - 100, max_length + 100)

            # Prioritas 4: Cari spasi biasa
            if split_pos == -1:
                split_pos = chunk.rfind(' ', max_length - 100, max_length + 100)

            # Jika tidak ada titik potong yang bagus, paksa potong di max_length
            if split_pos == -1:
                split_pos = max_length

            part = remaining[:split_pos].strip()
            if part:
                parts.append(part)

            remaining = remaining[split_pos:].strip()

        return parts

    async def _send_long_message(self, target, content: str, is_reply: bool = False, **embed_kwargs):
        """Kirim pesan panjang dengan membaginya menjadi beberapa pesan jika perlu.

        Args:
            target: discord.Message atau discord.Context (untuk reply/send)
            content: Isi pesan
            is_reply: Jika True, gunakan target.reply() untuk pesan pertama
            **embed_kwargs: Arguments untuk discord.Embed (color, dll)
        """
        if not content:
            return

        # Bersihkan response
        clean_content = self._clean_response(content)

        # Split menjadi beberapa bagian jika perlu
        parts = self._split_message(clean_content)

        for i, part in enumerate(parts):
            if is_reply and i == 0:
                # Pesan pertama: gunakan reply
                embed = discord.Embed(
                    description=part,
                    **embed_kwargs
                )
                await target.reply(embed=embed)
            elif i == 0 and hasattr(target, 'send'):
                # Pesan pertama tapi bukan reply (untuk !chat command)
                embed = discord.Embed(
                    description=part,
                    **embed_kwargs
                )
                await target.send(embed=embed)
            else:
                # Pesan selanjutnya: kirim sebagai pesan biasa di channel yang sama
                if is_reply:
                    channel = target.channel
                else:
                    channel = target.channel if hasattr(target, 'channel') else target

                embed = discord.Embed(
                    description=part,
                    **embed_kwargs
                )
                await channel.send(embed=embed)

    def _sanitize_prompt(self, prompt: str) -> str:
        """Sanitasi system prompt untuk memastikan tidak ada karakter berbahaya."""
        if not prompt:
            return ""
        # Hapus karakter null dan karakter kontrol berbahaya
        prompt = prompt.replace('\x00', '')
        # Kutip dan karakter lain aman karena akan di-escape oleh JSON library saat dikirim ke API
        return prompt.strip()

    def _is_reasoning_model(self, model: str) -> bool:
        """Cek apakah model adalah reasoning model."""
        reasoning_models = [
            'openai/gpt-oss-20b',
            'openai/gpt-oss-120b',
            'qwen/qwen3-32b'
        ]
        return model in reasoning_models

    def _get_reasoning_effort(self, model: str) -> str:
        """Dapatkan reasoning_effort untuk model. 'medium' adalah default yang baik."""
        if model in ['openai/gpt-oss-20b', 'openai/gpt-oss-120b']:
            return 'medium'  # low, medium, high
        elif model == 'qwen/qwen3-32b':
            return None  # Qwen uses 'none' or 'default', but we'll let it use default
        return None

    async def _call_groq_api(self, messages: List[Dict], api_key: str, temperature: float = 0.7, model: str = None) -> Optional[str]:
        """Panggil Groq API."""
        if not api_key:
            return None

        # Use provided model or fall back to config default
        if not model:
            model = getattr(config, 'GROQ_MODEL', 'llama-3.3-70b-versatile')

        # Log model being used
        reasoning_note = " (Reasoning)" if self._is_reasoning_model(model) else ""
        print(f"[Chatbot] 🤖 Using model: {model}{reasoning_note}")

        # Build request payload
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 2048  # Cukup untuk response panjang, lalu dipotong di 1900 karakter
        }

        # Add reasoning parameters for reasoning models
        if self._is_reasoning_model(model):
            reasoning_effort = self._get_reasoning_effort(model)
            if reasoning_effort:
                payload["reasoning_effort"] = reasoning_effort
            # reasoning_format: "parsed" gives structured reasoning, "hidden" hides it
            # Using "parsed" so we can see the reasoning process
            payload["reasoning_format"] = "parsed"
            print(f"[Chatbot] 🧠 Reasoning mode enabled: effort={reasoning_effort or 'default'}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=getattr(config, 'GROQ_TIMEOUT', 30))
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data['choices'][0]['message']['content']
                    else:
                        error_text = await resp.text()
                        print(f"Groq API error: {resp.status} - {error_text}")
                        return None
        except Exception as e:
            print(f"Error calling Groq API: {e}")
            return None

    def _has_image_attachments(self, message: discord.Message) -> bool:
        """Cek apakah message punya attachment gambar."""
        if not message.attachments:
            return False
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith('image/'):
                return True
        return False

    def _build_content_with_images(self, message: discord.Message, text: str) -> dict:
        """Build content dengan gambar untuk vision API.

        Returns:
            dict dengan format:
            - String biasa jika tidak ada gambar
            - List[dict] dengan text dan image_url jika ada gambar
        """
        if not self._has_image_attachments(message):
            return text

        # Ada gambar - build content array
        content = []

        # Tambah text prompt
        if text:
            content.append({
                "type": "text",
                "text": text
            })

        # Tambah semua gambar (max 5 images per Groq limit)
        image_count = 0
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith('image/'):
                if image_count < 5:
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": attachment.url
                        }
                    })
                    image_count += 1

        return content

    def _get_commands_knowledge(self) -> str:
        """Dapatkan daftar command yang tersedia untuk dijawab chatbot."""
        return """## Commands Knowledge Base

Prefix bot adalah `!` (default). Bot mendukung custom prefix per-server.

### Moderation Commands 🛡️
- `!kick <member> [reason]` - Kick member dari server
- `!ban <member> [reason]` - Ban member dari server
- `!unban <user_id>` - Unban user by ID
- `!mute <member> [duration_minutes] [reason]` - Mute/timeout member (alias: `timeout`)
- `!unmute <member>` - Hapus timeout dari member (alias: `untimeout`)
- `!clear [amount=10]` - Hapus pesan dari channel (alias: `purge`, `prune`)
- `!warn <member> [reason]` - Beri warn ke member
- `!slowmode [seconds=0]` - Set slowmode channel (0-21600 detik)
- `!lock` - Kunci channel (nonaktifkan @everyone kirim pesan)
- `!unlock` - Buka kunci channel

### Music Commands 🎵
- `!play <query>` - Putar lagu dari YouTube/Spotify (alias: `p`)
- `!pause` - Pause lagu
- `!resume` / `!unpause` - Lanjutkan lagu
- `!skip` - Skip ke lagu selanjutnya (alias: `s`, `next`)
- `!stop` - Stop player dan disconnect (alias: `disconnect`, `dc`, `leave`)
- `!queue [page=1]` - Tampilkan antrian lagu (alias: `q`)
- `!nowplaying` - Tampilkan lagu yang sedang diputar (alias: `np`, `current`)
- `!volume [0-100]` - Atur volume player (alias: `vol`, `v`)
- `!shuffle` - Acak antrian lagu
- `!loop [mode]` - Loop mode (off/single/all) (alias: `repeat`)
- `!remove <position>` - Hapus lagu dari antrian (alias: `rm`)
- `!clear_queue` - Hapus semua antrian (alias: `clearqueue`, `cq`)
- `!search <query>` - Cari lagu
- `!rplay [genre]` - Putar lagu random (alias: `randomplay`, `rp`)
- `!uplay [genre]` - Mode play unlimited (alias: `unlimitedplay`, `up`)
- `!lyrics` - Dapatkan lirik lagu (alias: `l`, `lyric`)

### Welcome Commands 🎉
- `!setwelcome [channel]` - Set channel untuk welcome message
- `!testwelcome` - Tes welcome message
- `!testgoodbye` - Tes goodbye message
- `!autorole [role]` - Set auto-role untuk member baru
- `!removeautorole` - Hapus setting auto-role
- `!welcomeinfo` - Tampilkan pengaturan welcome

### Leveling Commands 📊
- `!level [member]` - Tampilkan level Anda atau member lain (alias: `rank`, `xp`)
- `!leaderboard [page=1]` - Tampilkan leaderboard XP server (alias: `lb`, `top`)

**Admin Leveling (requires manage_guild):**
- `!setleveling toggle <enabled>` - Enable/disable leveling
- `!setleveling xp <amount>` - Set XP per pesan
- `!setleveling cooldown <seconds>` - Set cooldown XP
- `!setleveling minlength <length>` - Set min panjang pesan untuk XP
- `!setleveling channel [channel]` - Set channel notifikasi level-up
- `!setleveling notifications <enabled>` - Enable/disable notifikasi level-up
- `!levelrole add <level> <role> [stack]` - Tambah role reward untuk level
- `!levelrole remove <level> <role>` - Hapus level role reward
- `!resetxp <member>` - Reset XP user
- `!addxp <member> <amount>` - Tambah XP ke user
- `!fixxp [guild/all]` - Hitung ulang semua level

### Chatbot Commands 🤖
- `!chat <prompt>` atau `@Bot <prompt>` - Chat dengan AI (bisa di mana saja, termasuk reply pesan lain)
- `!chatchannel [channel]` - Set/enable chatbot channel
- `!chatbot` - Tampilkan pengaturan chatbot
- `!chatbot enable` - Enable chatbot di channel ini
- `!chatbot disable` - Disable chatbot
- `!chatbot channel [channel]` - Set chatbot channel (alias: `ch`)
- `!chatbot system <prompt>` - Set system prompt
- `!chatbot temperature <0.0-1.0>` - Set temperature (lebih tinggi = lebih kreatif)
- `!chatbot history [limit=10]` - Lihat chat history
- `!chatbot clearhistory` - Hapus chat history

### Help 📚
- `!help` - Tampilkan semua command
- `!help <command>` - Tampilkan detail command

**Catatan:** Jika user bertanya tentang prefix, command, atau fitur bot, gunakan informasi di atas untuk menjawab dengan jelas dan lengkap."""

    def _build_messages(self, content: str, settings: dict, history: List[Dict] = None) -> List[Dict]:
        """Build message array untuk API call."""
        messages = []

        # System prompt (custom user prompt)
        custom_system_prompt = settings.get('system_prompt', config.DEFAULT_SYSTEM_PROMPT)
        if custom_system_prompt:
            messages.append({
                "role": "system",
                "content": custom_system_prompt
            })

        # Commands knowledge - selalu sertakan agar bot bisa jawab pertanyaan tentang command
        messages.append({
            "role": "system",
            "content": self._get_commands_knowledge()
        })

        # Add history if available
        if history:
            max_history = settings.get('max_history', 10)
            for msg in history[-max_history:]:
                messages.append({
                    "role": msg.get('role', 'user'),
                    "content": msg.get('content', '')
                })

        # Current message
        messages.append({
            "role": "user",
            "content": content
        })

        return messages

    # ==================== EVENT LISTENER ====================

    def _is_bot_mentioned(self, message: discord.Message) -> bool:
        """Cek apakah bot di-mention dalam pesan."""
        return self.bot.user in message.mentions

    def _remove_bot_mention(self, content: str) -> str:
        """Hapus mention bot dari content pesan."""
        # Regex untuk menghapus mention bot (format <@123456789> atau <@!123456789>)
        bot_mention_patterns = [
            f'<@!?{self.bot.user.id}>',
            self.bot.user.mention,
            f'<@!{self.bot.user.id}>'
        ]

        cleaned = content
        for pattern in bot_mention_patterns:
            cleaned = cleaned.replace(pattern, '')

        return cleaned.strip()

    async def _process_mention_or_chat_command(self, message: discord.Message, prompt: str, is_mention: bool = False):
        """Process pesan yang mention bot atau menggunakan !chat command.

        Ini dipanggil dari on_message untuk mention, dan dari !chat command.
        Bekerja di mana saja (tidak harus di enabled channel).
        """
        guild_id = message.guild.id

        if not HAS_DATABASE:
            await message.reply("❌ Database tidak tersedia.")
            return

        db_settings = db.get_chatbot_settings(guild_id)
        if not db_settings or not db_settings.get('enabled', 0):
            # Untuk mention, beri pesan error lebih friendly
            if is_mention:
                await message.reply("❌ Chatbot belum di-enable. Gunakan **dashboard** atau `!chatchannel`")
            return

        api_key = db_settings.get('api_key') or config.GROQ_API_KEY
        if not api_key:
            await message.reply("❌ API Key belum di-set.")
            return

        # Cek apakah ini adalah reply ke pesan lain
        referenced_message = None
        has_reply_context = False
        reply_context = []

        if message.reference and message.reference.message_id:
            try:
                referenced_message = await message.channel.fetch_message(message.reference.message_id)
                has_reply_context = True

                # Build context dari pesan yang direply
                author_name = referenced_message.author.display_name
                author_mention = referenced_message.author.mention
                content = referenced_message.content or "(tanpa teks)"

                # Cek jika ada attachment gambar di pesan yang direply
                ref_has_images = self._has_image_attachments(referenced_message)

                reply_info = f"Pesan dari {author_name} ({author_mention}): {content}"

                # Jika ada gambar di pesan yang direply, tambahkan info
                if ref_has_images:
                    reply_info += "\n(Gambar terlampir)"

                reply_context.append(reply_info)

                print(f"[Chatbot] 💬 Reply context detected: {referenced_message.author.name}")
            except Exception as e:
                print(f"[Chatbot] Error fetching referenced message: {e}")

        # Process chat
        async with message.channel.typing():
            system_prompt_raw = db_settings.get('system_prompt', '')
            system_prompt = self._sanitize_prompt(system_prompt_raw) if system_prompt_raw and system_prompt_raw.strip() else ''

            messages = []

            # Custom system prompt if provided
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            # Commands knowledge - selalu sertakan agar bot bisa jawab pertanyaan tentang command
            messages.append({"role": "system", "content": self._get_commands_knowledge()})

            # Tentukan model
            model = db_settings.get('model_name') or db_settings.get('model', getattr(config, 'GROQ_MODEL', 'llama-3.3-70b-versatile'))

            # Cek vision untuk reply dengan gambar
            if has_reply_context and referenced_message and self._has_image_attachments(referenced_message):
                model = 'meta-llama/llama-4-scout-17b-16e-instruct'
                print(f"[Chatbot] 🖼️ Reply contains image! Using vision model: {model}")

                # Build content dengan gambar untuk vision
                vision_content = self._build_content_with_images(referenced_message, f"Pertanyaan tentang pesan/gambar ini: {prompt}")
                messages.append({"role": "user", "content": vision_content})
            # Jika ada reply context tapi bukan gambar
            elif has_reply_context and reply_context:
                context_prompt = "Berikut adalah konteks pesan yang ditanyakan:\n" + "\n".join(reply_context) + f"\n\nPertanyaan: {prompt}"
                messages.append({"role": "user", "content": context_prompt})
            else:
                # Tambahkan prompt langsung tanpa context
                messages.append({"role": "user", "content": prompt})

            response = await self._call_groq_api(messages, api_key, db_settings.get('temperature', 0.7), model)

            if response:
                # Send response dengan auto-split jika panjang
                await self._send_long_message(
                    message,
                    response,
                    is_reply=True,
                    color=config.COLORS.get("chatbot", 0x00D9FF)
                )
            else:
                await message.reply("❌ Error saat memproses pesan.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen untuk pesan dan response.

        Behaviour:
        1. Jika bot di-mention -> respon di mana saja
        2. Jika pesan mengandung !chat -> abaikan (biar command handle)
        3. Jika di enabled channel -> respon otomatis
        """
        # Skip bot messages dan DMs
        if message.author.bot or not message.guild:
            return

        guild_id = message.guild.id
        channel_id = message.channel.id

        # Get settings from database directly (no caching)
        if not HAS_DATABASE:
            return

        db_settings = db.get_chatbot_settings(guild_id)
        if not db_settings:
            return  # No settings configured

        # Parse settings
        enabled = db_settings.get('enabled', 0) == 1
        enabled_channels = db_settings.get('enabled_channels', [])
        # Convert enabled_channels to strings for comparison (handles both int and string from DB)
        enabled_channels_str = [str(ch) for ch in enabled_channels]
        api_key = db_settings.get('api_key') or config.GROQ_API_KEY

        # Check if bot is mentioned
        is_mentioned = self._is_bot_mentioned(message)

        # Jika bot di-mention, proses (bekerja di mana saja)
        if is_mentioned:
            # Hapus mention dari content
            prompt = self._remove_bot_mention(message.content)

            # Jika hanya mention tanpa teks, beri pesan default
            if not prompt and not self._has_image_attachments(message):
                await message.reply("Hai! Ada yang bisa dibantu? Ketik pertanyaan atau command setelah mention.")
                return

            # Proses mention dengan reply context support
            await self._process_mention_or_chat_command(message, prompt, is_mention=True)
            return

        # Jika tidak di-mention, cek apakah command !chat
        prefix = getattr(config, 'PREFIX', '!')
        prompt = message.content.strip()
        if prompt.startswith(f'{prefix}chat'):
            return  # Let the !chat command handle it

        # Check all conditions untuk auto-respon di enabled channel
        if not enabled:
            return  # Chatbot not enabled
        if not api_key:
            return  # No API key
        if str(channel_id) not in enabled_channels_str:
            return  # Not in enabled channel

        # Get the message content for auto-respon
        has_images = self._has_image_attachments(message)

        # Allow empty prompt if there are images
        if not prompt and not has_images:
            return  # Empty message and no images

        # Process the message (auto-respon di enabled channel)
        async with message.channel.typing():
            # Get history (skip if has images - vision context works better without history)
            history = [] if has_images else db.get_chat_history(guild_id, channel_id, limit=db_settings.get('max_history', 10))

            # Build messages (includes custom system prompt + commands knowledge)
            system_prompt_raw = db_settings.get('system_prompt', '')
            system_prompt = self._sanitize_prompt(system_prompt_raw) if system_prompt_raw and system_prompt_raw.strip() else ''

            messages = []

            # Custom system prompt if provided
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            # Commands knowledge - selalu sertakan agar bot bisa jawab pertanyaan tentang command
            messages.append({"role": "system", "content": self._get_commands_knowledge()})

            # Add history (skip if has images)
            if not has_images:
                for msg in history:
                    role = "user" if msg.get('role') == "user" else "assistant"
                    messages.append({"role": role, "content": msg.get('content', '')})

            # Build user content (with or without images)
            # Default prompt for images only
            image_prompt = prompt if prompt else "Apa yang ada di gambar ini? Jelaskan dengan detail."
            user_content = self._build_content_with_images(message, image_prompt)

            # Add current message
            messages.append({"role": "user", "content": user_content})

            # Use vision model if there are images
            if has_images:
                model = 'meta-llama/llama-4-scout-17b-16e-instruct'
                print(f"[Chatbot] 🖼️ Image detected! Using vision model: {model}")
            else:
                model = db_settings.get('model_name') or db_settings.get('model', getattr(config, 'GROQ_MODEL', 'llama-3.3-70b-versatile'))

            # Call API
            response = await self._call_groq_api(messages, api_key, db_settings.get('temperature', 0.7), model)

            if response:
                # Send response dengan auto-split jika panjang
                await self._send_long_message(
                    message,
                    response,
                    is_reply=True,
                    color=config.COLORS.get("chatbot", 0x00D9FF)
                )

                # Save to history (simpan full cleaned version)
                clean_response = self._clean_response(response)
                db.add_chat_message(guild_id, channel_id, message.author.id, "user", prompt)
                db.add_chat_message(guild_id, channel_id, self.bot.user.id, "assistant", clean_response)
            else:
                await message.reply("❌ Maaf, terjadi error. Coba lagi.")

    # ==================== CHAT COMMAND ====================

    @commands.command(name="chat")
    async def chat(self, ctx: commands.Context, *, prompt: str):
        """Chat dengan AI. Bisa digunakan di mana saja, termasuk sebagai reply pesan lain."""
        guild_id = ctx.guild.id

        # Get settings directly from database
        if not HAS_DATABASE:
            return await ctx.send("❌ Database tidak tersedia.")

        db_settings = db.get_chatbot_settings(guild_id)
        if not db_settings or not db_settings.get('enabled', 0):
            return await ctx.send("❌ Chatbot belum di-enable. Gunakan **dashboard** atau `!chatchannel`")

        api_key = db_settings.get('api_key') or config.GROQ_API_KEY
        if not api_key:
            return await ctx.send("❌ API Key belum di-set. Cek di **config.py** atau **dashboard**.")

        # Cek apakah ini adalah reply ke pesan lain
        referenced_message = None
        has_reply_context = False
        reply_context = []

        if ctx.message.reference and ctx.message.reference.message_id:
            try:
                referenced_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                has_reply_context = True

                # Build context dari pesan yang direply
                author_name = referenced_message.author.display_name
                author_mention = referenced_message.author.mention
                content = referenced_message.content or "(tanpa teks)"

                # Cek jika ada attachment gambar di pesan yang direply
                ref_has_images = self._has_image_attachments(referenced_message)

                reply_info = f"Pesan dari {author_name} ({author_mention}): {content}"

                # Jika ada gambar di pesan yang direply, tambahkan info
                if ref_has_images:
                    reply_info += "\n(Gambar terlampir)"

                reply_context.append(reply_info)

                # Jika ada gambar, siapkan content dengan gambar
                if ref_has_images:
                    # Build content dengan gambar dari pesan yang direply
                    image_content = self._build_content_with_images(referenced_message, "")
                    if isinstance(image_content, list):
                        # Ada gambar - convert ke format yang sesuai
                        reply_context.append("Gambar dari pesan yang direply:")
                        for item in image_content:
                            if item.get("type") == "image_url":
                                reply_context.append(f"[Gambar: {item['image_url']['url']}]")

                print(f"[Chatbot] 💬 Reply context detected: {referenced_message.author.name}")
            except Exception as e:
                print(f"[Chatbot] Error fetching referenced message: {e}")

        # Process chat
        async with ctx.typing():
            system_prompt_raw = db_settings.get('system_prompt', '')
            system_prompt = self._sanitize_prompt(system_prompt_raw) if system_prompt_raw and system_prompt_raw.strip() else ''

            messages = []

            # Custom system prompt if provided
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            # Commands knowledge - selalu sertakan agar bot bisa jawab pertanyaan tentang command
            messages.append({"role": "system", "content": self._get_commands_knowledge()})

            # Jika ada reply context, tambahkan sebagai context
            if has_reply_context and reply_context:
                context_prompt = "Berikut adalah konteks pesan yang ditanyakan:\n" + "\n".join(reply_context) + f"\n\nPertanyaan: {prompt}"
                messages.append({"role": "user", "content": context_prompt})
            else:
                # Tambahkan prompt langsung tanpa context
                messages.append({"role": "user", "content": prompt})

            # Tentukan model - gunakan vision model jika reply ke pesan dengan gambar
            model = db_settings.get('model_name') or db_settings.get('model', getattr(config, 'GROQ_MODEL', 'llama-3.3-70b-versatile'))

            if has_reply_context and referenced_message and self._has_image_attachments(referenced_message):
                model = 'meta-llama/llama-4-scout-17b-16e-instruct'
                print(f"[Chatbot] 🖼️ Reply contains image! Using vision model: {model}")

                # Rebuild messages untuk vision API
                if system_prompt:
                    messages = [{"role": "system", "content": system_prompt}]
                messages.append({"role": "system", "content": self._get_commands_knowledge()})

                # Build content dengan gambar untuk vision
                vision_content = self._build_content_with_images(referenced_message, f"Pertanyaan tentang pesan/gambar ini: {prompt}")
                messages.append({"role": "user", "content": vision_content})

            response = await self._call_groq_api(messages, api_key, db_settings.get('temperature', 0.7), model)

            if response:
                # Send response dengan auto-split jika panjang
                await self._send_long_message(
                    ctx,
                    response,
                    is_reply=False,
                    color=config.COLORS.get("chatbot", 0x00D9FF)
                )
            else:
                await ctx.send("❌ Error saat memproses pesan.")

    # ==================== CHATCHANNEL SHORTCUT COMMAND ====================

    @commands.command(name="chatchannel")
    @commands.has_permissions(manage_guild=True)
    async def chatchannel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Set chatbot channel. Otomatis enable chatbot di channel ini."""
        if not channel:
            channel = ctx.channel

        if HAS_DATABASE:
            # Get current settings and update - also ENABLE automatically
            current_settings = db.get_chatbot_settings(ctx.guild.id) or {}
            current_settings['enabled'] = True  # Auto enable!
            current_settings['enabled_channels'] = [channel.id]
            db.save_chatbot_settings(ctx.guild.id, current_settings)

        embed = self._create_embed(
            "✅ Chatbot Ready!",
            f"Chatbot aktif di {channel.mention}!\n"
            f"Ketik pesan apa saja untuk chat dengan AI.\n\n"
            f"Gunakan **dashboard** untuk pengaturan lanjutan.",
            config.COLORS["success"]
        )
        await ctx.send(embed=embed)

    # ==================== ADMIN COMMANDS ====================

    @commands.group(name="chatbot", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def chatbot(self, ctx: commands.Context):
        """Kelola pengaturan chatbot."""
        settings = self._get_settings(ctx.guild.id)

        enabled_channels = settings.get('enabled_channels', [])
        channel_mention = "None"
        if enabled_channels:
            # Convert to int for get_channel (handles both string and int)
            channel_id = int(enabled_channels[0]) if enabled_channels else None
            ch = ctx.guild.get_channel(channel_id) if channel_id else None
            if ch:
                channel_mention = ch.mention

        description = "**🤖 Chatbot Settings:**\n\n"
        description += f"📊 **Status:** {'✅ Enabled' if settings.get('enabled') else '❌ Disabled'}\n"
        description += f"📢 **Chatbot Channel:** {channel_mention}\n"
        description += f"🌡️ **Temperature:** {settings.get('temperature', 0.7)}\n"
        description += f"📝 **Max History:** {settings.get('max_history', 10)} messages\n"
        description += f"\n💡 Gunakan `!chatchannel` untuk set channel chatbot!"

        embed = discord.Embed(
            description=description,
            color=config.COLORS["info"]
        )
        await ctx.send(embed=embed)

    @chatbot.command(name="enable")
    @commands.has_permissions(manage_guild=True)
    async def chatbot_enable(self, ctx: commands.Context):
        """Enable chatbot dan set channel saat ini."""
        if HAS_DATABASE:
            # Enable dan set channel ini
            settings = self._get_settings(ctx.guild.id)
            settings['enabled'] = True
            settings['enabled_channels'] = [ctx.channel.id]
            db.save_chatbot_settings(ctx.guild.id, settings)

        embed = self._create_embed(
            "✅ Chatbot Enabled",
            f"Chatbot aktif di {ctx.channel.mention}!\n\n"
            f"Gunakan **dashboard** untuk pengaturan lengkap (channel, API key, dll).",
            config.COLORS["success"]
        )
        await ctx.send(embed=embed)

    @chatbot.command(name="disable")
    @commands.has_permissions(manage_guild=True)
    async def chatbot_disable(self, ctx: commands.Context):
        """Disable chatbot untuk guild."""
        if HAS_DATABASE:
            db.toggle_chatbot(ctx.guild.id, False)

        embed = self._create_embed(
            "✅ Chatbot Disabled",
            "Chatbot telah dimatikan. Gunakan **dashboard** untuk mengaktifkan kembali.",
            config.COLORS["success"]
        )
        await ctx.send(embed=embed)

    @chatbot.command(name="channel", aliases=["ch"])
    @commands.has_permissions(manage_guild=True)
    async def chatbot_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Set chatbot channel (hanya 1 channel yang dipilih)."""
        if not channel:
            channel = ctx.channel

        if HAS_DATABASE:
            # Set single channel (replace, not append)
            settings = self._get_settings(ctx.guild.id)
            settings['enabled_channels'] = [channel.id]
            db.save_chatbot_settings(ctx.guild.id, settings)

        embed = self._create_embed(
            "✅ Chatbot Channel Set",
            f"{channel.mention} adalah SATU-SATUNYA channel untuk chatbot.\n"
            f"Bot hanya akan merespon di channel ini!",
            config.COLORS["success"]
        )
        await ctx.send(embed=embed)

    @chatbot.command(name="system")
    @commands.has_permissions(manage_guild=True)
    async def chatbot_system(self, ctx: commands.Context, *, prompt: str):
        """Set system prompt untuk chatbot."""
        # Sanitasi prompt untuk menghilangkan karakter berbahaya
        sanitized_prompt = self._sanitize_prompt(prompt)
        if HAS_DATABASE:
            settings = self._get_settings(ctx.guild.id)
            settings['system_prompt'] = sanitized_prompt
            db.save_chatbot_settings(ctx.guild.id, settings)

        embed = self._create_embed(
            "✅ System Prompt Updated",
            f"System prompt telah diupdate!\n\n**Prompt:** {sanitized_prompt[:200]}{'...' if len(sanitized_prompt) > 200 else ''}",
            config.COLORS["success"]
        )
        await ctx.send(embed=embed)

    @chatbot.command(name="temperature")
    @commands.has_permissions(manage_guild=True)
    async def chatbot_temperature(self, ctx: commands.Context, temp: float):
        """Set temperature (0.0 - 1.0)."""
        temp = max(0.0, min(1.0, temp))

        if HAS_DATABASE:
            settings = self._get_settings(ctx.guild.id)
            settings['temperature'] = temp
            db.save_chatbot_settings(ctx.guild.id, settings)

        embed = self._create_embed(
            "✅ Temperature Updated",
            f"Temperature di-set ke **{temp}**.\nLebih tinggi = lebih kreatif, Lebih rendah = lebih fokus.",
            config.COLORS["success"]
        )
        await ctx.send(embed=embed)

    @chatbot.command(name="history")
    @commands.has_permissions(manage_guild=True)
    async def chatbot_history(self, ctx: commands.Context, limit: int = 10):
        """Lihat chat history."""
        if not HAS_DATABASE:
            return await ctx.send("Database tidak tersedia.")

        history = db.get_chat_history(ctx.guild.id, ctx.channel.id, limit=limit)

        if not history:
            embed = self._create_embed(
                "📜 Chat History",
                "Tidak ada history untuk channel ini.",
                config.COLORS["info"]
            )
            return await ctx.send(embed=embed)

        description = ""
        for msg in history:
            role = msg.get('role', 'user')
            content = msg.get('content', '')[:100]
            if role == 'user':
                user_id = msg.get('user_id')
                member = ctx.guild.get_member(user_id)
                name = member.display_name if member else f"<@{user_id}>"
                description += f"👤 **{name}:** {content}...\n\n"
            else:
                description += f"🤖 **Bot:** {content}...\n\n"

        embed = discord.Embed(
            title=f"📜 Chat History - {ctx.channel.name}",
            description=description,
            color=config.COLORS["info"]
        )
        await ctx.send(embed=embed)

    @chatbot.command(name="clearhistory")
    @commands.has_permissions(manage_guild=True)
    async def chatbot_clear_history(self, ctx: commands.Context):
        """Hapus chat history untuk channel ini."""
        if HAS_DATABASE:
            db.clear_chat_history(ctx.guild.id, ctx.channel.id)

        embed = self._create_embed(
            "✅ History Cleared",
            f"Chat history untuk {ctx.channel.mention} telah dihapus.",
            config.COLORS["success"]
        )
        await ctx.send(embed=embed)

    # ==================== ERROR HANDLER ====================

    @chat.error
    @chatbot_enable.error
    @chatbot_disable.error
    @chatbot_channel.error
    @chatbot_system.error
    @chatbot_temperature.error
    @chatbot_history.error
    @chatbot_clear_history.error
    @chatchannel.error
    async def chatbot_error(self, ctx: commands.Context, error):
        """Handle chatbot command errors."""
        if isinstance(error, commands.MissingPermissions):
            embed = self._create_embed(
                "❌ Missing Permissions",
                "Kamu butuh permission **Manage Server** untuk command ini!",
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

    def cog_unload(self):
        """Cleanup saat cog unload."""
        if self.session:
            asyncio.create_task(self.session.close())


# ==================== SETUP FUNCTION ====================

async def setup(bot: commands.Bot):
    """Setup function untuk load cog."""
    await bot.add_cog(Chatbot(bot))
