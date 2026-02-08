# Setup Domain untuk Discord Bot + Dashboard

Domain: `moonlit-bot.my.id`
Provider: Domainesia
Tunnel: Cloudflare Tunnel

## Gambaran Arsitektur

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  User Browser   │ ──> │ Cloudflare Tunnel │ ──> │  Flask Server   │
│ (moonlit-bot...) │     │     (cloudflared)   │     │  :5001          │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                         │
                                                         ▼
                                                  ┌─────────────────┐
                                                  │ Discord Bot     │
                                                  │ (run.py)        │
                                                  └─────────────────┘
```

---

## Bagian 1: Setting DNS di Domainesia

### 1. Login ke Domainesia

1. Buka https://member.domainesia.com
2. Login dengan akun Anda

### 2. Cari Domain Anda

1. Masuk ke menu **Domain** -> **My Domains**
2. Klik tombol **Manage** pada domain `moonlit-bot.my.id`

### 3. Ubah Nameserver ke Cloudflare

Jika Anda sudah punya akun Cloudflare:

1. Buka [Cloudflare](https://dash.cloudflare.com/sign-up)
2. Add Site: `moonlit-bot.my.id`
3. Pilih plan **Free**
4. Cloudflare akan memberikan 2 nameserver, contoh:
   - `alice.ns.cloudflare.com`
   - `bob.ns.cloudflare.com`

5. Kembali ke **Domainesia**:
   - Cari menu **Nameserver** atau **Change Nameservers**
   - Pilih **Custom Nameservers**
   - Masukkan 2 nameserver dari Cloudflare
   - Klik **Save**

6. Tunggu 24-48 jam untuk propagasi (biasanya 10-30 menit)

---

## Bagian 2: Setting Cloudflare Tunnel

### 1. Install cloudflared di Windows (PC Saat Ini)

**Download cloudflared:**
1. Buka https://github.com/cloudflare/cloudflared/releases
2. Download versi terbaru untuk Windows: `cloudflared-windows-amd64.msi`
3. Install seperti biasa

**Atau via Winget:**
```powershell
winget install Cloudflare.cloudflared
```

**Cek instalasi:**
```powershell
cloudflared --version
```

### 2. Login ke Cloudflare

Buka PowerShell / CMD:

```powershell
# Login akan membuka browser
cloudflared tunnel login
```

1. Browser akan terbuka
2. Pilih domain `moonlit-bot.my.id`
3. Authorize

### 3. Buat Tunnel

```powershell
# Buat tunnel baru dengan nama "discord-bot"
cloudflared tunnel create discord-bot
```

Output akan menampilkan **Tunnel ID**, simpan! Contoh:
```
Tunnel ID: abc123-def456-ghi789
```

### 4. Buat File Konfigurasi

Buat file `cloudflared.yml` di folder project (atau di `C:\Users\<User>\.cloudflared\`):

```yaml
# File: cloudflared.yml
tunnel: abc123-def456-ghi789  # Ganti dengan Tunnel ID Anda

credentials-file: C:\Users\<YourUser>\.cloudflared\<tunnel-id>.json  # Ganti path sesuai

ingress:
  # Dashboard Flask
  - hostname: moonlit-bot.my.id
    service: http://localhost:5001

  # Atau subdomain untuk dashboard:
  # - hostname: dashboard.moonlit-bot.my.id
  #   service: http://localhost:5001

  # Fallback untuk traffic lain
  - service: http_status:404
```

### 5. Jalankan Tunnel

**Opsi A: Jalankan Manual (Untuk Testing)**

```powershell
# Dari folder project
cloudflared tunnel --config cloudflared.yml run
```

**Opsi B: Jalankan sebagai Service (Windows)**

```powershell
# Install sebagai service
cloudflared service install

# Set config file (sesuaikan path)
sc config cloudflared start=auto
```

Atau edit registry:
1. Win + R, ketik `regedit`
2. Navigate ke: `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\cloudflared`
3. Edit `ImagePath`, tambahkan `--config C:\path\to\cloudflared.yml`

---

## Bagian 3: Update Konfigurasi Bot

### 1. Update .env

```env
# Discord Bot Token
DISCORD_BOT_TOKEN=MTQ2NjUyMTQ0OTQ5MjY0ODA5OQ.GHFtoU.TnA1MO12bO4dKKaW9WZqhN-sJRNKjWMbAaDmek

# Discord OAuth2 (untuk Dashboard)
DISCORD_CLIENT_ID=1466521449492648099
DISCORD_CLIENT_SECRET=rwO6suW9n5ot26WFs3d0iDPCsoHG52Hf

# UPDATE: Redirect URI pakai domain Anda
DISCORD_REDIRECT_URI=https://moonlit-bot.my.id/callback

# Dashboard Base URL - UPDATE dengan domain Anda
DASHBOARD_BASE_URL=https://moonlit-bot.my.id

# Dashboard Secret Key
DASHBOARD_SECRET_KEY=rahasia_disini_buat_random

# Database (PostgreSQL/Supabase)
DATABASE_URL=postgresql://postgres.cnjsflffoywmzhebospy:Kurnia7928*@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres

# Groq API Key (untuk Chatbot)
GROQ_API_KEY=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
```

### 2. Update Discord Developer Portal

1. Buka https://discord.com/developers/applications
2. Pilih aplikasi bot Anda
3. Masuk ke **OAuth2** -> **General**
4. Di **Redirects**, tambahkan:
   - `https://moonlit-bot.my.id/callback`
5. Klik **Save Changes**

---

## Bagian 4: Setting di Linux (PC Server)

### 1. Install cloudflared di Linux

**Debian/Ubuntu:**
```bash
# Download
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb

# Install
sudo dpkg -i cloudflared-linux-amd64.deb
```

**CentOS/RHEL:**
```bash
# Download
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-x86_64.rpm

# Install
sudo rpm -i cloudflared-linux-x86_64.rpm
```

### 2. Login dan Setup Tunnel

```bash
# Login
cloudflared tunnel login

# Buat tunnel baru (atau gunakan tunnel yang sama)
cloudflared tunnel create discord-bot-linux

# Atau gunakan tunnel ID yang sama dari Windows
```

### 3. Buat Konfigurasi di Linux

Buat file `/etc/cloudflared/config.yml`:

```yaml
tunnel: <tunnel-id-anda-dari-windows>

credentials-file: /home/<user>/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: moonlit-bot.my.id
    service: http://localhost:5001
  - service: http_status:404
```

### 4. Jalankan sebagai Service (Linux)

```bash
# Install service
sudo cloudflared service install

# Enable auto-start
sudo systemctl enable cloudflared

# Start service
sudo systemctl start cloudflared

# Cek status
sudo systemctl status cloudflared
```

### 5. Clone dan Jalankan Bot

```bash
# Clone repository
git clone https://github.com/JhonyKurniawan/DiscordBotMoonlit.git
cd DiscordBotMoonlit

# Install Python (jika belum)
sudo apt update
sudo apt install python3 python3-pip

# Install dependencies
pip3 install -r requirements.txt

# Jalankan bot
python3 run.py
```

---

## Bagian 5: Testing

### 1. Cek Cloudflare Tunnel

Di Windows/Linux, jalankan:
```powershell
# Windows
cloudflared tunnel info discord-bot

# Linux
cloudflared tunnel info discord-bot-linux
```

Status harus: **Healthy**

### 2. Cek DNS

Di komputer Anda:
```powershell
nslookup moonlit-bot.my.id
```

Harus menunjuk ke Cloudflare IP

### 3. Akses Dashboard

Buka browser: https://moonlit-bot.my.id

Dashboard harus terbuka!

### 4. Test Discord OAuth

1. Klik "Login with Discord"
2. Authorize aplikasi
3. Harus redirect ke dashboard dengan berhasil

---

## Bagian 6: Subdomain (Opsional)

Jika mau pisahkan dashboard dan API:

```yaml
ingress:
  # Dashboard
  - hostname: moonlit-bot.my.id
    service: http://localhost:5001

  # API (jika ada port berbeda)
  - hostname: api.moonlit-bot.my.id
    service: http://localhost:5000

  # Atau subdomain lain
  - hostname: status.moonlit-bot.my.id
    service: http://localhost:3000

  - service: http_status:404
```

Untuk menambahkan subdomain di Cloudflare:
1. Masuk ke Cloudflare Dashboard
2. DNS -> Records
3. Add Record:
   - Type: **CNAME**
   - Name: `dashboard` (atau `api`, `status`, dll)
   - Target: `moonlit-bot.my.id`
   - Proxy: **ON** (orange cloud)

---

## Troubleshooting

### Tunnel tidak connect

```powershell
# Cek log tunnel
cloudflared tunnel run discord-bot --loglevel debug
```

### 404 saat akses domain

1. Cek apakah Flask server jalan di port 5001
2. Cek konfigurasi ingress di cloudflared.yml
3. Cek hostname sudah benar

### Discord OAuth error "Redirect URI mismatch"

1. Pastikan redirect URI di Discord Developer Portal sesuai:
   - `https://moonlit-bot.my.id/callback`
2. Pastikan HTTPS (bukan HTTP)

### Tunnel expired

```powershell
# Hapus tunnel lama
cloudflared tunnel delete <tunnel-id>

# Buat baru
cloudflared tunnel create discord-bot
```

### Linux service tidak jalan

```bash
# Cek log
sudo journalctl -u cloudflared -f

# Restart service
sudo systemctl restart cloudflared
```

---

## Ringkasan Ports

| Service | Local Port | Domain |
|---------|-----------|--------|
| Dashboard Flask | 5001 | moonlit-bot.my.id |
| Bot (internal) | - | - |

---

## Keamanan Tambahan

### 1. Enable HTTPS di Cloudflare

1. Cloudflare Dashboard -> SSL/TLS
2. Set mode: **Full** atau **Full (Strict)**
3. Always Use HTTPS: **ON**

### 2. Firewall Rules (Opsional)

Cloudflare Dashboard -> Security -> WAF -> Custom Rules:

```yaml
# Rule: Block selain Indonesia
(ip.geo.country ne "ID") and (http.host eq "moonlit-bot.my.id")
Action: Block
```

### 3. Rate Limiting

Cloudflare Dashboard -> Security -> Rate Limiting Rules:

- Limit: 100 requests per minute
- Action: Challenge

---

## Script Start Otomatis (Windows)

Buat file `start-all.bat`:

```batch
@echo off
echo Starting Discord Bot and Cloudflare Tunnel...

start "Cloudflare Tunnel" cmd /c "cloudflared tunnel --config cloudflared.yml run"
timeout /t 5
start "Discord Bot" cmd /c "python run.py"

echo All services started!
pause
```

---

## Script Start Otomatis (Linux)

Buat file `start-all.sh`:

```bash
#!/bin/bash

echo "Starting Discord Bot and Cloudflare Tunnel..."

# Start cloudflared service
sudo systemctl start cloudflared

# Start bot
cd /home/user/DiscordBotMoonlit
python3 run.py
```

Jadikan executable:
```bash
chmod +x start-all.sh
```

---

## Checklist

- [ ] Nameserver di Domainesia diubah ke Cloudflare
- [ ] Cloudflare Tunnel dibuat
- [ ] cloudflared terinstall di Windows
- [ ] cloudflared terinstall di Linux
- [ ] File .env sudah diupdate dengan domain
- [ ] Discord Developer Portal redirect URI sudah diupdate
- [ ] Tunnel berjalan di Windows/Linux
- [ ] Bot bisa diakses via https://moonlit-bot.my.id
