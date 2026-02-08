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
copy .env.example .env
copy config.example.py config.py

# Edit .env dan config.py sesuai kebutuhan
notepad .env
notepad config.py

# Jalankan bot
python run.py
```

## Persyaratan

- Python 3.10+
- MongoDB (opsional, tergantung config)

## Fitur

- Leveling system dengan XP
- Welcome card & goodbye message
- Dashboard web untuk monitoring
- Custom commands
- Dan lainnya

## Struktur Project

```
DiscordBotMoonlit/
├── bot.py              # Konfigurasi bot utama
├── run.py              # Entry point bot
├── config.py           # File konfigurasi (buat dari config.example.py)
├── requirements.txt    # Dependencies Python
├── cogs/               # Folder commands bot
├── dashboard/          # Dashboard web (Frontend + Backend)
├── utils/              # Utility functions
└── uploads/            # Folder upload gambar
```

## Dokumentasi

- [TUTORIAL.md](TUTORIAL.md) - Tutorial lengkap menjalankan bot
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

## Catatan Penting

- File `.env` berisi token rahasia dan TIDAK di-track di git
- File `config.py` perlu dibuat manual dari `config.example.py`
- Repository ini bersifat **PRIVATE**

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| Module not found | `pip install -r requirements.txt` |
| Token invalid | Cek file `.env` |
| Python tidak dikenali | Install Python 3.10+ |

Lihat [TUTORIAL.md](TUTORIAL.md) untuk panduan lengkap.
