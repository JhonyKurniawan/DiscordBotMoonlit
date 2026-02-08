# Deployment Guide Lengkap - Discord Bot Moonlit

Update terakhir: Februari 2026

---

## Daftar Isi

1. [Persiapan Awal](#1-persiapan-awal)
2. [Setup Domain (Domainesia)](#2-setup-domain-domainesia)
3. [Setup Cloudflare](#3-setup-cloudflare)
4. [Setup Cloudflare Tunnel](#4-setup-cloudflare-tunnel)
5. [Setup Bot di Lokal](#5-setup-bot-di-lokal)
6. [Database & LLM Configuration](#6-database--llm-configuration)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Persiapan Awal

### Persyaratan Sistem

| Komponen | Versi Minimum |
|----------|--------------|
| Python | 3.10+ |
| Node.js | 18+ |
| Git | Latest |
| OS | Windows/Linux |

### Tools yang Dibutuhkan

- **Python**: https://python.org
- **Node.js**: https://nodejs.org
- **Git**: https://git-scm.com
- **Cloudflare Tunnel**: https://github.com/cloudflare/cloudflared/releases

---

## 2. Setup Domain (Domainesia)

### 2.1 Beli Domain

1. Buka https://domainesia.com
2. Cari domain yang diinginkan
3. Checkout dan selesaikan pembayaran

### 2.2 Ubah Nameserver ke Cloudflare

1. Login ke https://member.domainesia.com
2. Menu **Domain** → **My Domains**
3. Klik **Manage** pada domain yang dipilih
4. Cari menu **Nameserver** atau **Change Nameservers**
5. Pilih **Custom Nameservers**
6. Masukkan nameserver Cloudflare:

**Untuk dapat nameserver Cloudflare:**
- Buka https://dash.cloudflare.com/sign-up
- Add Site dengan domain Anda
- Pilih plan **Free**
- Cloudflare akan memberikan 2 nameserver, contoh:
  ```
  alice.ns.cloudflare.com
  bob.ns.cloudflare.com
  ```

7. Di Domainesia, masukkan 2 nameserver tersebut
8. Klik **Save**
9. Tunggu 24-48 jam (biasanya 10-30 menit)

### 2.3 Cek Propagasi DNS

```bash
# Windows
nslookup namadomainanda.my.id

# Linux/Mac
dig namadomainanda.my.id
```

Harus menunjuk ke IP Cloudflare.

---

## 3. Setup Cloudflare

### 3.1 Tambah Domain ke Cloudflare

1. Login ke https://dash.cloudflare.com
2. Klik **Add a Site**
3. Masukkan domain Anda
4. Pilih plan **Free**
5. Cloudflare akan scan DNS records Anda

### 3.2 Setup DNS Records

Setelah nameserver aktif, buat DNS records:

**DNS → Records → Add Record**

| Type | Name | Content | Proxy | TTL |
|------|------|---------|-------|-----|
| A | @ | 192.0.2.1 | Proxied (ON) | Auto |
| CNAME | api | yourdomain.my.id | Proxied (ON) | Auto |

**Catatan:** IP `192.0.2.1` adalah dummy IP karena kita pakai tunnel.

### 3.3 Setup SSL/TLS

1. **SSL/TLS** → **Overview**
2. Set mode ke **Flexible** atau **Full**
3. Pastikan **Always Use HTTPS** = ON
4. Pastikan **Automatic HTTPS Rewrites** = ON

---

## 4. Setup Cloudflare Tunnel

### 4.1 Install cloudflared

**Windows:**
```powershell
# Download dari: https://github.com/cloudflare/cloudflared/releases
# Atau pakai winget:
winget install Cloudflare.cloudflared

# Cek instalasi
cloudflared --version
```

**Linux (Debian/Ubuntu):**
```bash
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```

**Linux (CentOS/RHEL):**
```bash
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-x86_64.rpm
sudo rpm -i cloudflared-linux-x86_64.rpm
```

### 4.2 Login ke Cloudflare

```bash
cloudflared tunnel login
```

Browser akan terbuka. Pilih domain Anda dan authorize.

### 4.3 Buat Tunnel

```bash
# Buat tunnel baru
cloudflared tunnel create discord-bot

# Output akan menampilkan Tunnel ID, simpan!
# Contoh:
# Tunnel ID: abc123-def456-ghi789
# Credentials file: /path/to/.cloudflared/abc123-def456-ghi789.json
```

### 4.4 Buat Konfigurasi Tunnel

Buat file `cloudflared.yml` di root project:

```yaml
# Cloudflare Tunnel Configuration
tunnel: <TUNNEL_ID_ANDA>

# Windows
credentials-file: C:\Users\<Username>\.cloudflared\<TUNNEL_ID>.json

# Linux
# credentials-file: /home/<user>/.cloudflared/<TUNNEL_ID>.json

ingress:
  # Frontend (Vue)
  - hostname: yourdomain.my.id
    service: http://localhost:5190

  # Backend API (Flask)
  - hostname: api.yourdomain.my.id
    service: http://localhost:5001

  # Fallback
  - service: http_status:404
```

### 4.5 Jalankan Tunnel

**Untuk testing:**
```bash
cloudflared tunnel --config cloudflared.yml run
```

**Sebagai service (Windows):**
```powershell
cloudflared service install
```

**Sebagai service (Linux):**
```bash
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

---

## 5. Setup Bot di Lokal

### 5.1 Clone Repository

```bash
git clone https://github.com/JhonyKurniawan/DiscordBotMoonlit.git
cd DiscordBotMoonlit
```

### 5.2 Install Python Dependencies

```bash
# Windows
pip install -r requirements.txt

# Linux
pip3 install -r requirements.txt
```

### 5.3 Install Node Dependencies (Frontend)

```bash
cd dashboard/frontend
npm install
```

### 5.4 Konfigurasi Environment

**File `.env` di root:**
```env
# Discord Bot Token
DISCORD_BOT_TOKEN=token_bot_anda

# Discord OAuth2
DISCORD_CLIENT_ID=client_id_anda
DISCORD_CLIENT_SECRET=client_secret_anda
DISCORD_REDIRECT_URI=https://api.yourdomain.my.id/callback

# Dashboard
DASHBOARD_SECRET_KEY=rahasia_disini
DASHBOARD_BASE_URL=https://yourdomain.my.id

# Database
DATABASE_URL=postgresql://user:pass@host:port/db

# LLM API
GROQ_API_KEY=gsk_xxxx Anda
```

**File `dashboard/frontend/.env`:**
```env
VITE_DISCORD_CLIENT_ID=client_id_anda
VITE_REDIRECT_URI=https://api.yourdomain.my.id/callback
VITE_API_URL=https://api.yourdomain.my.id/api
```

### 5.5 Update Discord Developer Portal

1. Buka https://discord.com/developers/applications
2. Pilih aplikasi bot Anda
3. **OAuth2** → **General**
4. Di **Redirects**, tambahkan:
   ```
   https://api.yourdomain.my.id/callback
   ```
5. Klik **Save Changes**

### 5.6 Update Vite Config untuk Network

**File `dashboard/frontend/package.json`:**
```json
{
  "scripts": {
    "dev": "vite --host 0.0.0.0",
    "build": "vite build"
  }
}
```

Ini penting agar Vite bisa diakses dari luar localhost.

### 5.7 Jalankan Semua Service

**Terminal 1 - Discord Bot:**
```bash
cd D:\Project\DiscordBotNothing
python run.py
```

**Terminal 2 - Flask Backend:**
```bash
cd D:\Project\DiscordBotNothing
python -m dashboard.backend.app
```

**Terminal 3 - Vue Frontend:**
```bash
cd D:\Project\DiscordBotNothing\dashboard\frontend
npm run dev
```

**Terminal 4 - Cloudflare Tunnel:**
```bash
cloudflared tunnel --config cloudflared.yml run
```

### 5.8 Script Start Otomatis (Windows)

**File `start-all.bat`:**
```batch
@echo off
title Discord Bot Moonlit

echo Starting Discord Bot Moonlit...
echo.

echo [1/4] Starting Cloudflare Tunnel...
start "Cloudflare Tunnel" cmd /c "cloudflared tunnel --config cloudflared.yml run"
timeout /t 3 >nul

echo [2/4] Starting Flask Backend...
start "Flask Backend" cmd /c "python -m dashboard.backend.app"
timeout /t 3 >nul

echo [3/4] Starting Vue Frontend...
cd dashboard\frontend
start "Vue Frontend" cmd /c "npm run dev"
cd ..\..
timeout /t 5 >nul

echo [4/4] Starting Discord Bot...
python run.py

pause
```

---

## 6. Database & LLM Configuration

### 6.1 Database Options

#### Option 1: Supabase (PostgreSQL) - Recommended

1. Buka https://supabase.com
2. Create new project
3. Get database connection string:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres
   ```

#### Option 2: Neon (PostgreSQL)

1. Buka https://neon.tech
2. Create project
3. Get connection string

#### Option 3: Railway (PostgreSQL)

1. Buka https://railway.app
2. New Project → PostgreSQL
3. Get connection string

### 6.2 LLM API Options (Februari 2026)

#### Groq (Recommended - Fast & Free)

**Website:** https://groq.com

**Models Available (Februari 2026):**
- `llama-3.3-70b-versatile` - General purpose, fast
- `llama-3.1-8b-instant` - Super fast, good for simple tasks
- `mixtral-8x7b-32768` - Good for complex reasoning
- `gemma2-9b-it` - Google model, balanced

**Get API Key:**
1. Buka https://console.groq.com
2. Login/Register
3. Go to **API Keys**
4. Create new key
5. Copy key

**Pricing (Februari 2026):**
- Free tier: 500 requests/day
- Pay-as-you-go: $0.19 per million tokens

**Configuration:**
```python
GROQ_API_KEY = "gsk_xxxx..."
GROQ_MODEL = "llama-3.3-70b-versatile"
```

#### OpenAI (GPT-4/GPT-4o)

**Website:** https://platform.openai.com

**Models Available (Februari 2026):**
- `gpt-4o` - Latest GPT-4 Omni, multimodal
- `gpt-4o-mini` - Cheaper, faster
- `gpt-4-turbo` - GPT-4 Turbo
- `o1-mini` - Reasoning model

**Pricing (Februari 2026):**
- gpt-4o: $5 per million input tokens
- gpt-4o-mini: $0.15 per million input tokens
- o1-mini: $1.10 per million input tokens

**Configuration:**
```python
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-4o"
```

#### Anthropic Claude

**Website:** https://console.anthropic.com

**Models Available (Februari 2026):**
- `claude-3-5-sonnet-20241022` - Balanced
- `claude-3-5-haiku-20241022` - Fast, cheap
- `claude-3-opus-20240229` - Most capable

**Pricing (Februari 2026):**
- Sonnet: $3 per million input tokens
- Haiku: $0.25 per million input tokens
- Opus: $15 per million input tokens

**Configuration:**
```python
ANTHROPIC_API_KEY = "sk-ant-..."
ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"
```

#### Google Gemini

**Website:** https://ai.google.dev

**Models Available (Februari 2026):**
- `gemini-2.0-flash` - Latest, multimodal
- `gemini-2.0-flash-thinking` - With reasoning
- `gemini-1.5-pro` - Previous generation

**Pricing (Februari 2026):**
- Free tier available
- Pay-as-you-go: Very competitive

**Configuration:**
```python
GOOGLE_API_KEY = "AIza..."
GOOGLE_MODEL = "gemini-2.0-flash"
```

### 6.3 LLM Comparison (Februari 2026)

| Provider | Model | Speed | Quality | Price (per 1M tokens) |
|----------|-------|-------|---------|---------------------|
| Groq | llama-3.3-70b | ⚡⚡⚡ Fastest | 🟢 Good | $0.19 |
| OpenAI | gpt-4o | ⚡⚡ Fast | 🟢🟢 Great | $5.00 |
| Anthropic | claude-3-5-sonnet | ⚡⚡ Fast | 🟢🟢🟢 Excellent | $3.00 |
| Google | gemini-2.0-flash | ⚡⚡⚡ Very Fast | 🟢🟢 Great | ~$0.075 |

### 6.4 Bot Configuration untuk LLM

**File `config.py`:**
```python
# ==================== CHATBOT CONFIGURATION ====================

# Groq (Recommended)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_TIMEOUT = 30

# Atau OpenAI
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
# OPENAI_MODEL = "gpt-4o"

# Atau Anthropic
# ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
# ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"

# System prompt
DEFAULT_SYSTEM_PROMPT = "Kamu bot Discord yang helpful dan friendly."

# Maximum chat history
MAX_CHAT_HISTORY = 20
```

---

## 7. Troubleshooting

### 7.1 Website Tidak Bisa Diakses (522 Error)

**Masalah:** Cloudflare bisa connect tapi timeout ke server lokal.

**Solusi:**
1. Pastikan Vite jalan dengan `--host 0.0.0.0`
2. Cek apakah service jalan di port yang benar:
   ```bash
   # Windows
   netstat -ano | findstr :5190
   netstat -ano | findstr :5001

   # Linux
   lsof -i :5190
   lsof -i :5001
   ```
3. Restart tunnel:
   ```bash
   # Stop tunnel (Ctrl+C)
   cloudflared tunnel --config cloudflared.yml run
   ```

### 7.2 DNS Tidak Resolve

**Cek:**
```bash
nslookup yourdomain.my.id
```

**Solusi:**
1. Tunggu propagasi DNS (10-30 menit)
2. Pastikan nameserver di registrar sudah benar (Cloudflare)
3. Cek DNS records di Cloudflare

### 7.3 SSL Error (ERR_SSL_VERSION_OR_CIPHER_MISMATCH)

**Solusi:**
1. Di Cloudflare Dashboard → SSL/TLS → Overview
2. Ubah mode ke **Flexible**
3. Tunggu 1-2 menit
4. Refresh browser

### 7.4 Discord OAuth Error

**Masalah:** Redirect URI mismatch

**Solusi:**
1. Pastikan redirect URI di Discord Developer Portal sama dengan di `.env`
2. Format harus persis:
   ```
   https://api.yourdomain.my.id/callback
   ```
3. Tidak boleh ada trailing slash di akhir

### 7.5 Vite Hanya Jalan di Localhost

**Tanda:**
```
➜ Local: http://localhost:5190/
➜ Network: use --host to expose
```

**Solusi:**
Ubah `package.json`:
```json
"dev": "vite --host 0.0.0.0"
```

### 7.6 Tunnel Tidak Connect

**Cek tunnel status:**
```bash
cloudflared tunnel info discord-bot
```

**Solusi:**
1. Pastikan credentials file path benar
2. Pastikan tunnel ID benar
3. Cek log untuk error

### 7.7 Flask Import Error

**Error:**
```
ImportError: attempted relative import with no known parent package
```

**Solusi:**
Jangan jalankan `app.py` langsung. Gunakan:
```bash
python -m dashboard.backend.app
```

---

## 8. Maintenance

### 8.1 Update Bot

```bash
git pull
pip install -r requirements.txt --upgrade
```

### 8.2 Backup Database

```bash
# Supabase - otomatis
# Neon - otomatis
# Atau export manual dari dashboard
```

### 8.3 Monitor Logs

```bash
# Cloudflare Tunnel logs
cloudflared tunnel info discord-bot

# Bot logs ada di terminal
```

---

## 9. Summary Checklist

Sebelum deployment, pastikan:

- [ ] Domain sudah dibeli dan nameserver diubah ke Cloudflare
- [ ] DNS records sudah dibuat di Cloudflare (@ dan api)
- [ ] SSL/TLS mode sudah di-set (Flexible/Full)
- [ ] Cloudflare Tunnel sudah dibuat dan konfigurasi
- [ ] cloudflared sudah terinstall
- [ ] Project sudah di-clone
- [ ] Python dependencies sudah terinstall
- [ ] Node dependencies sudah terinstall
- [ ] `.env` sudah diisi dengan benar
- [ ] Discord Developer Portal redirect URI sudah di-set
- [ ] Vite config sudah di-set `--host 0.0.0.0`
- [ ] Database sudah siap (Supabase/Neon/Railway)
- [ ] LLM API key sudah didapat (Groq/OpenAI/etc)
- [ ] Semua service berjalan (Bot, Flask, Vue, Tunnel)
- [ ] Website bisa diakses via domain

---

## 10. Links Penting

- **Cloudflare Dashboard**: https://dash.cloudflare.com
- **Discord Developer Portal**: https://discord.com/developers/applications
- **Groq Console**: https://console.groq.com
- **OpenAI Platform**: https://platform.openai.com
- **Supabase**: https://supabase.com
- **Domainesia**: https://member.domainesia.com

---

*Dokumentasi ini diupdate terakhir pada Februari 2026*
*Untuk pertanyaan atau issues, buat issue di GitHub repository*
