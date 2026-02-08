# Discord Bot Moonlit

Bot Discord dengan fitur leveling, welcome card, dashboard web, dan lainnya.

## Persyaratan

- Python 3.10+
- pip

## Cara Install

1. Clone repository:
```bash
git clone https://github.com/JhonyKurniawan/DiscordBotMoonlit.git
cd DiscordBotMoonlit
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Konfigurasi environment:
```bash
# Copy file .env.example ke .env
copy .env.example .env

# Atau buat file .env manual dan isi sesuai konfigurasi
```

4. Buat file config:
```bash
# Copy file config.example.py ke config.py
copy config.example.py

# Edit file config.py dan isi sesuai kebutuhan
notepad config.py
```

5. Jalankan bot:
```bash
python run.py
```

---

## Tutorial Menjalankan Bot

### Langkah 1: Persiapan Environment

Pastikan sudah memiliki:
- Python 3.10 atau lebih baru
- Token Bot Discord (dari https://discord.com/developers/applications)
- MongoDB Atlas connection string (jika menggunakan MongoDB)

### Langkah 2: Konfigurasi File

#### A. File .env
Buat file `.env` di root folder:

```env
# Discord Bot Token
DISCORD_TOKEN=token_bot_anda_disini
DISCORD_CLIENT_ID=client_id_bot_anda

# MongoDB (jika digunakan)
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/database

# API Keys (jika diperlukan)
API_KEY=api_key_anda
```

#### B. File config.py
Copy dari `config.example.py` dan sesuaikan:

```python
# Prefix bot
PREFIX = "!"

# Owner ID
OWNER_ID = 123456789012345678

# Server/Guild ID
GUILD_ID = 123456789012345678

# Channel ID (untuk welcome, log, dll)
WELCOME_CHANNEL_ID = 123456789012345678
LOG_CHANNEL_ID = 123456789012345678
```

### Langkah 3: Menjalankan Bot

#### Opsi 1: Menjalankan Bot Saja
```bash
python run.py
```

#### Opsi 2: Menjalankan dengan Dashboard
```bash
# Terminal 1 - Jalankan Bot
python run.py

# Terminal 2 - Jalankan Dashboard
cd dashboard/backend
python app.py
```

#### Opsi 3: Menjalankan dengan Batch File (Windows)
```bash
# Double click file run.bat
run.bat
```

### Langkah 4: Verifikasi Bot Berjalan

Jika berhasil, Anda akan melihat:
```
[INFO] Bot sedang login...
[INFO] Bot berhasil login sebagai NamaBot#1234
[INFO] Bot siap! Logged in sebagai NamaBot#1234
```

Cek di Discord, bot应该 sudah online.

### Menjalankan di Background (Opsional)

#### Windows - Menggunakan hidden start
```bash
start /B python run.py
```

#### Linux - Menggunakan screen atau tmux
```bash
# Menggunakan screen
screen -S discordbot
python run.py
# Tekan Ctrl+A, lalu D untuk detach

# Untuk kembali ke screen
screen -r discordbot
```

### Menjalankan di Startup

#### Windows Task Scheduler
1. Buka Task Scheduler
2. Create Basic Task
3. Set trigger: "When I log on" atau "At startup"
4. Action: "Start a program"
5. Program: `python.exe`
6. Arguments: `"D:\Project\DiscordBotNothing\run.py"`
7. Start in: `"D:\Project\DiscordBotNothing"`

---

## Cara Update (Upload & Sync)

### Upload Perubahan ke GitHub

Dari PC tempat Anda mengedit code:

```bash
# 1. Cek status file yang berubah
git status

# 2. Tambahkan semua perubahan
git add .

# 3. Commit dengan pesan
git commit -m "pesan perubahan anda"

# 4. Push ke GitHub
git push
```

### Mengambil Update di PC Lain

Dari PC lain yang ingin di-update:

```bash
# Ambil perubahan terbaru dari GitHub
git pull
```

## Perintah Singkat Git

| Perintah | Keterangan |
|----------|------------|
| `git status` | Cek status file yang berubah |
| `git add .` | Tambah semua perubahan |
| `git add <file>` | Tambah file spesifik |
| `git commit -m "pesan"` | Commit perubahan |
| `git push` | Upload ke GitHub |
| `git pull` | Download dari GitHub |
| `git log --oneline -5` | Lihat 5 commit terakhir |

## Struktur Project

```
DiscordBotMoonlit/
├── bot.py              # Konfigurasi bot utama
├── run.py              # Entry point menjalankan bot
├── config.py           # File konfigurasi (buat dari config.example.py)
├── requirements.txt    # Dependencies Python
├── cogs/               # Folder commands bot
├── dashboard/          # Dashboard web (Frontend + Backend)
├── utils/              # Utility functions
└── uploads/            # Folder upload gambar
```

## Catatan Penting

- File `.env` berisi token rahasia dan TIDAK di-track di git
- File `config.py` perlu dibuat manual dari `config.example.py`
- Repository ini bersifat **PRIVATE** - jangan dibuat public

## Troublehooting

### Bot tidak jalan
- Pastikan Python versi 10+ terinstall
- Cek file `.env` sudah terisi dengan benar
- Pastikan semua dependencies terinstall: `pip install -r requirements.txt`

### Git push minta password
- Gunakan Personal Access Token (PAT) GitHub, bukan password akun
- Buat PAT di: https://github.com/settings/tokens

### Git pull ada conflict
```bash
# Simpan perubahan lokal terlebih dahulu
git stash
git pull
git stash pop
```
