# Discord Bot Moonlit

Bot Discord dengan fitur leveling, welcome card, dashboard web, dan lainnya.

## Quick Start

```bash
# Clone repository
git clone https://github.com/JhonyKurniawan/DiscordBotMoonlit.git
cd DiscordBotMoonlit

# Install dependencies
pip install -r requirements.txt

# Jalankan bot
python run.py
```

## Persyaratan

- Python 3.10+
- PostgreSQL/Supabase

## Fitur

- Leveling system dengan XP
- Welcome card & goodbye message
- Dashboard web untuk monitoring
- Custom commands
- Chatbot dengan AI (Groq)
- Music player
- Dan lainnya

## Akses Bot

- **Dashboard**: https://moonlit-bot.my.id
- **Domain**: moonlit-bot.my.id (via Cloudflare Tunnel)

## Struktur Project

```
DiscordBotMoonlit/
├── bot.py              # Konfigurasi bot utama
├── run.py              # Entry point bot
├── config.py           # File konfigurasi
├── .env                # Environment variables
├── requirements.txt    # Dependencies Python
├── cloudflared.yml     # Konfigurasi Cloudflare Tunnel
├── cogs/               # Folder commands bot
├── dashboard/          # Dashboard web (Frontend + Backend)
├── utils/              # Utility functions
└── uploads/            # Folder upload gambar
```

## Dokumentasi

- [TUTORIAL.md](TUTORIAL.md) - Tutorial lengkap menjalankan bot
- [DOMAIN_SETUP.md](DOMAIN_SETUP.md) - Tutorial setup domain & Cloudflare Tunnel
- [Cara Update](#cara-update-upload--sync) - Upload & sync ke PC lain

## Cara Update (Upload & Sync)

### Upload Perubahan ke GitHub

Dari PC tempat Anda mengedit code:

```bash
git add .
git commit -m "pesan perubahan"
git push
```

### Mengambil Update di PC Lain

```bash
git pull
```

## Perintah Git Singkat

| Perintah | Keterangan |
|----------|------------|
| `git status` | Cek status file yang berubah |
| `git add .` | Tambah semua perubahan |
| `git commit -m "pesan"` | Commit perubahan |
| `git push` | Upload ke GitHub |
| `git pull` | Download dari GitHub |

## Konfigurasi Domain

Project ini menggunakan:
- **Domain**: moonlit-bot.my.id
- **Tunnel**: Cloudflare Tunnel (cloudflared)
- **Dashboard Port**: 5001

File konfigurasi:
- `.env` - Environment variables (redirect URI, base URL)
- `config.py` - Konfigurasi bot dan dashboard
- `cloudflared.yml` - Konfigurasi Cloudflare Tunnel

## Catatan Penting

- File `.env` dan `config.py` sudah tersedia dan ter-include di repository
- Repository ini bersifat **PRIVATE**
- Pastikan Cloudflare Tunnel berjalan sebelum mengakses dashboard

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| Module not found | `pip install -r requirements.txt` |
| Token invalid | Cek file `.env` |
| Python tidak dikenali | Install Python 3.10+ |
| Dashboard tidak accessible | Pastikan cloudflared tunnel berjalan |

Lihat [TUTORIAL.md](TUTORIAL.md) untuk panduan lengkap.
Lihat [DOMAIN_SETUP.md](DOMAIN_SETUP.md) untuk setup domain.
