# Discord Bot Moonlit

Bot Discord dengan fitur leveling, welcome card, dashboard web, dan lainnya.

## Quick Start

```bash
# Clone repository
git clone https://github.com/JhonyKurniawan/DiscordBotMoonlit.git
cd DiscordBotMoonlit

# Install dependencies
pip install -r requirements.txt

# Setup konfigurasi
# Copy .env.example ke .env dan isi sesuai kebutuhan
# Copy config.example.py ke config.py dan isi sesuai kebutuhan

# Jalankan bot
python run.py
```

## Deploy to WispByte

This project can be deployed to [WispByte](https://wispbyte.com) for free hosting.

### Setup Instructions:

1. Create account at https://wispbyte.com
2. Click "New Project"
3. Select "Import from GitHub"
4. Enter repository: `JhonyKurniawan/DiscordBotMoonlit`
5. Configure environment variables (see below)
6. Deploy!

### Environment Variables for WispByte:

| Variable | Description | Example |
|----------|-------------|---------|
| `DISCORD_BOT_TOKEN` | Discord Bot Token | `MTQ2NjUyMTQ0OTQ5MjY0ODA5OQ...` |
| `DISCORD_CLIENT_ID` | Discord Client ID | `1466521449492648099` |
| `DISCORD_CLIENT_SECRET` | Discord Client Secret | `rwo6suw9n5ot...` |
| `DISCORD_REDIRECT_URI` | Redirect URI for OAuth2 | `https://your-domain.wispbyte.app/callback` |
| `DASHBOARD_SECRET_KEY` | Flask secret key | `random-secret-key` |
| `DASHBOARD_BASE_URL` | Dashboard base URL | `https://your-domain.wispbyte.app` |
| `DATABASE_URL` | PostgreSQL/Supabase URI | `postgresql://...` |
| `GROQ_API_KEY` | Groq API key for chatbot | `gsk_xxxx...` |

## Persyaratan

- Python 3.10+
- PostgreSQL/Supabase
- Groq API key (untuk chatbot)

## Fitur

- Leveling system dengan XP
- Welcome card & goodbye message
- Dashboard web untuk monitoring
- Custom commands
- Chatbot dengan AI (Groq)
- Music player
- Dan lainnya

## Akses Bot

- **Dashboard**: https://moonlit-bot.my.id (when self-hosted)
- **Deploy**: https://wispbyte.com (free hosting)

## Cara Update (Upload & Sync)

### Upload Perubahan ke GitHub

```bash
git add .
git commit -m "pesan perubahan"
git push
```

### Update di WispByte

WispByte akan otomatis deploy saat Kamu push ke GitHub.

## Struktur Project

```
DiscordBotMoonlit/
├── bot.py              # Konfigurasi bot utama
├── run.py              # Entry point bot
├── config.py           # File konfigurasi
├── requirements.txt    # Dependencies Python
├── wispbyte.json      # WispByte deployment config
├── cogs/               # Folder commands bot
├── dashboard/          # Dashboard web (Frontend + Backend)
├── utils/              # Utility functions
└── uploads/            # Folder upload gambar
```

## Dokumentasi

- [TUTORIAL.md](TUTORIAL.md) - Tutorial lengkap menjalankan bot
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Deployment guide lengkap

## Catatan Penting

- File `.env` dan `config.py` sudah tersedia dan ter-include di repository
- Repository ini bersifat **PRIVATE**

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| Module not found | `pip install -r requirements.txt` |
| Token invalid | Cek environment variables di WispByte dashboard |
| Python tidak dikenali | Install Python 3.10+ |

Lihat [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) untuk informasi lebih lanjut.
