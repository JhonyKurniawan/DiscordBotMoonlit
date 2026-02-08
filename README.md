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

4. Jalankan bot:
```bash
python run.py
```

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
