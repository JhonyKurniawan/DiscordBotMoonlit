# Tutorial Menjalankan Bot

Panduan lengkap cara menjalankan Discord Bot Moonlit.

## Daftar Isi

1. [Persiapan](#langkah-1-persiapan-environment)
2. [Konfigurasi](#langkah-2-konfigurasi-file)
3. [Menjalankan](#langkah-3-menjalankan-bot)
4. [Verifikasi](#langkah-4-verifikasi-bot-berjalan)
5. [Background](#menjalankan-di-background)
6. [Auto-start](#menjalankan-di-startup)

---

## Langkah 1: Persiapan Environment

### Persyaratan Sistem

Pastikan sudah terinstall:

| Software | Versi Minimum | Cara Cek |
|----------|--------------|----------|
| Python | 3.10+ | `python --version` |
| pip | Latest | `pip --version` |
| Git | Latest | `git --version` |

### Mendapatkan Token Bot Discord

1. Buka [Discord Developer Portal](https://discord.com/developers/applications)
2. Klik "New Application"
3. Beri nama bot, klik "Create"
4. Masuk ke menu "Bot" -> "Add Bot"
5. Copy **Bot Token** (diperlukan untuk `.env`)

### Mendapatkan Credentials Lainnya

- **Client ID**: Di halaman General Information -> Application ID
- **MongoDB URI** (jika pakai MongoDB): Buat cluster di [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)

---

## Langkah 2: Konfigurasi File

### A. File .env

Buat file `.env` di root folder (sejajar dengan `run.py`):

```env
# ===== Discord Bot =====
DISCORD_TOKEN=isi_token_bot_disini
DISCORD_CLIENT_ID=isi_client_id_disini

# ===== MongoDB (jika digunakan) =====
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/dbname

# ===== API Keys (opsional) =====
API_KEY=api_key_anda
```

**Catatan:** Jangan share file `.env` ke orang lain! Berisi token rahasia.

### B. File config.py

1. Copy file `config.example.py`
2. Rename menjadi `config.py`
3. Edit sesuai kebutuhan:

```python
# ===== Bot Configuration =====
PREFIX = "!"              # Prefix command bot
OWNER_ID = 1234567890    # ID Discord owner
GUILD_ID = 1234567890    # ID server Discord

# ===== Channel IDs =====
WELCOME_CHANNEL_ID = 1234567890  # Channel untuk welcome message
LOG_CHANNEL_ID = 1234567890      # Channel untuk log bot
LEAVE_CHANNEL_ID = 1234567890    # Channel untuk goodbye message

# ===== Leveling System =====
ENABLE_LEVELING = True
LEVEL_UP_CHANNEL_ID = 1234567890

# ===== Dashboard =====
DASHBOARD_PORT = 5000
DASHBOARD_SECRET_KEY = "rahasia_disini"
```

**Cara Mendapatkan Channel/Server ID:**

1. Aktifkan Developer Mode di Discord (Settings -> Advanced -> Developer Mode)
2. Klik kanan server/channel -> Copy ID

---

## Langkah 3: Menjalankan Bot

### Opsi 1: Menjalankan Bot Saja

Buka terminal/cmd di folder project:

```bash
# Windows
python run.py

# Linux/Mac
python3 run.py
```

### Opsi 2: Menjalankan Bot + Dashboard

**Terminal 1 - Jalankan Bot:**
```bash
python run.py
```

**Terminal 2 - Jalankan Dashboard:**
```bash
cd dashboard/backend
python app.py
```

Dashboard akan accessible di: `http://localhost:5000`

### Opsi 3: Menggunakan Batch File (Windows)

Double click file `run.bat` atau buat baru:

```batch
@echo off
echo Starting Discord Bot...
python run.py
pause
```

### Opsi 4: Menggunakan Shell Script (Linux/Mac)

Buat file `start.sh`:

```bash
#!/bin/bash
echo "Starting Discord Bot..."
python3 run.py
```

Jalankan:
```bash
chmod +x start.sh
./start.sh
```

---

## Langkah 4: Verifikasi Bot Berjalan

### Output yang Benar

Jika berhasil, terminal akan menampilkan:

```
═══════════════════════════════════════════════
    DISCORD BOT MOONLIT
═══════════════════════════════════════════════

[INFO] Loading cogs...
[INFO] Loading commands...
[INFO] Bot sedang login...
[SUCCESS] Bot berhasil login sebagai NamaBot#1234
[SUCCESS] Bot siap! Logged in sebagai NamaBot#1234
[INFO] Serving on 0.0.0.0:5000 (Dashboard)
```

### Cek di Discord

1. Buka server Discord Anda
2. Bot harus online (indikator hijau)
3. Coba ketik command (contoh: `!ping`)
4. Bot harus merespons

### Jika Bot Offline

| Masalah | Solusi |
|---------|--------|
| Token invalid | Cek lagi token di `.env` |
| Module not found | Jalankan `pip install -r requirements.txt` |
| Connection error | Cek internet connection |
| Permission denied | Pastikan Python punya akses folder |

---

## Menjalankan di Background

### Windows

#### Method 1: Hidden Start
```bash
start /B python run.py
```

#### Method 2: VBScript
Buat file `run_hidden.vbs`:
```vbscript
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "python run.py", 0
Set WshShell = Nothing
```

### Linux / macOS

#### Menggunakan screen
```bash
# Install screen (jika belum)
sudo apt install screen  # Ubuntu/Debian
sudo yum install screen  # CentOS/RHEL

# Buat screen baru
screen -S discordbot

# Jalankan bot
python3 run.py

# Detach (biarkan jalan di background)
# Tekan: Ctrl + A, lalu tekan D

# Untuk kembali ke screen
screen -r discordbot

# List semua screen
screen -ls
```

#### Menggunakan tmux
```bash
# Install tmux
sudo apt install tmux

# Buat session baru
tmux new -s discordbot

# Jalankan bot
python3 run.py

# Detach
# Tekan: Ctrl + B, lalu tekan D

# Untuk kembali
tmux attach -t discordbot
```

#### Menggunakan nohup
```bash
nohup python3 run.py > bot.log 2>&1 &

# Cek log
tail -f bot.log

# Stop bot
pkill -f "python3 run.py"
```

---

## Menjalankan di Startup

### Windows - Task Scheduler

1. Buka **Task Scheduler**
2. Klik **Create Basic Task**
3. Name: `Discord Bot Moonlit`
4. Trigger: **When I log on** atau **At startup**
5. Action: **Start a program**
6. Program/script:
   ```
   C:\Users\YourUser\AppData\Local\Programs\Python\Python310\python.exe
   ```
7. Add arguments:
   ```
   "D:\Project\DiscordBotNothing\run.py"
   ```
8. Start in:
   ```
   D:\Project\DiscordBotNothing
   ```
9. Finish

### Windows - Startup Folder

1. Tekan `Win + R`
2. Ketik `shell:startup`
3. Buat shortcut ke `run.bat` atau buat file batch

### Linux - systemd Service

Buat file `/etc/systemd/system/discordbot.service`:

```ini
[Unit]
Description=Discord Bot Moonlit
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/your_username/DiscordBotMoonlit
ExecStart=/usr/bin/python3 /home/your_username/DiscordBotMoonlit/run.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable dan start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable discordbot
sudo systemctl start discordbot
sudo systemctl status discordbot
```

### Linux - Crontab

```bash
crontab -e
```

Tambahkan:
```bash
@reboot cd /home/user/DiscordBotMoonlit && python3 run.py
```

---

## Troubleshooting

### Python tidak dikenali

**Windows:**
```bash
# Tambahkan Python ke PATH
# Atau gunakan py launcher
py run.py
```

**Linux/Mac:**
```bash
# Gunakan python3
python3 run.py
```

### ModuleNotFoundError

```bash
# Install ulang dependencies
pip install -r requirements.txt

# Atau upgrade pip
pip install --upgrade pip
```

### Discord Login Failed

1. Cek token di `.env` - pastikan tidak ada spasi
2. Regenerate token di Discord Developer Portal jika perlu
3. Pastikan bot belum di-delete

### Port Already in Use

```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <pid> /F

# Linux
lsof -i :5000
kill -9 <pid>
```

### Database Connection Error

1. Cek koneksi internet
2. Verify MongoDB URI
3. Pastikan IP address ter-whitelist di MongoDB Atlas

---

## Commands Dasar Bot

Setelah bot berjalan, coba command berikut:

| Command | Deskripsi |
|---------|-----------|
| `!ping` | Cek latency bot |
| `!help` | Tampilkan semua command |
| `!userinfo @user` | Info user |
| `!level` | Cek level Anda |

---

## Support

Jika mengalami masalah:
1. Cek log di terminal
2. Baca file log jika ada
3. Pastikan semua config sudah benar
