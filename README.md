# AutoLogin GSuite

Alat otomatis untuk login banyak akun Google Workspace (GSuite) sekaligus ke satu profil Chrome, tanpa kehilangan akun yang sudah ada.

Cara kerja: login dilakukan di **profil Chrome terpisah** (profil kustom) karena Chrome modern memblokir otomasi di profil utama, lalu hasilnya disinkronkan kembali ke Chrome utama yang biasa kamu pakai.

> Dibuat & dikembangkan oleh [**rzkyfhrzi21**](https://github.com/rzkyfhrzi21) — Instagram: [**@rzkydev666**](https://instagram.com/rzkydev666)

---

## Fitur

| Fitur | Keterangan |
|---|---|
| Login massal otomatis | Email & password terisi otomatis dari `akungsuite.txt`, 1 tab per akun |
| Anti-deteksi otomasi | Stealth script (webdriver spoof, plugin, language) + ketik dengan delay manusia |
| Deteksi captcha otomatis | Saat halaman captcha muncul: password kedua terisi otomatis, script **berhenti aman** — kamu tinggal isi captcha & klik setuju manual |
| Deteksi ToS/consent | Halaman "Workspace Terms of Service" dideteksi, tab dibiarkan untuk persetujuan manual |
| Akun lama tidak hilang | Pipeline `prepare → push` selalu menyinkronkan penuh, jadi akun yang sudah ada **tidak pernah terhapus** |
| Backup otomatis | Setiap file yang akan diubah di-backup dulu (folder `.backup-sync-*`) |
| Pengaman Chrome | Script menolak berjalan jika Chrome masih terbuka (mencegah file tertimpa dari memori) |
| Mode tes | `--limit N` untuk mencoba hanya N akun pertama |

---

## Kebutuhan (setiap perangkat baru)

1. **Python 3.11+** — unduh di [python.org](https://www.python.org/downloads/) (centang *Add to PATH* saat install)
2. **Google Chrome** — [google.com/chrome](https://www.google.com/chrome/) (versi apa pun, terbaru disarankan)
3. **Playwright (Python)** — jalankan di CMD:
   ```cmd
   pip install playwright
   ```

Tidak perlu `playwright install chromium` — script memakai Chrome yang sudah terpasang.

---

## Setup Awal (sekali per perangkat)

1. **Cek path Chrome** di `login.py` (variabel `CHROME_PATH`):
   ```python
   CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
   ```
   Sesuaikan jika lokasi Chrome kamu berbeda.

2. **Sesuaikan path profil utama** di `sync.py` (variabel `MAIN_ROOT`) — ganti `rizky` dengan nama user Windows kamu:
   ```python
   MAIN_ROOT = Path(r"C:\Users\rizky\AppData\Local\Google\Chrome\User Data")
   ```

3. **Isi daftar akun** di `akungsuite.txt` (format `email|password`, satu per baris):
   ```
   # AKUN GSUITE UNTUK AUTO LOGIN
   # Format: email|password (satu akun per baris)
   # Baris yang diawali # diabaikan (komentar)

   akun1@perusahaan.com|password1
   akun2@perusahaan.com|password2
   ```

4. **Buka Chrome sekali**, login manual akun utama kamu (misal akun pribadi), lalu **tutup Chrome** — profil utama harus dalam keadaan berisi akun yang sudah ada sebelum mulai.

---

## Penggunaan

> **⚠️ Aturan emas: Chrome harus TERTUTUP sebelum menjalankan `sync.py`** (script otomatis menolak jika Chrome masih jalan).

### Alur 1 — Tambah akun baru

```cmd
python sync.py prepare
```
*Menyalin profil utama → profil kustom (snapshot terbaru, akun lama ikut terbawa).*

```cmd
python login.py
```
*Membuka Chrome kustom, mengisi email + password semua akun di `akungsuite.txt`. Berhenti otomatis di halaman captcha / ToS. Kamu selesaikan manual: isi captcha → klik Next → setuju, di tiap tab. Setelah selesai, **tutup Chrome**.*

```cmd
python sync.py push
```
*Menyalin hasil login dari profil kustom → profil utama. Akun lama tetap, akun baru bertambah.*

**Buka Chrome utama → semua akun sudah ada di avatar.**

### Alur 2 — Cek status

```cmd
python sync.py status
```
*Menampilkan daftar akun di profil utama & kustom, dan status Chrome.*

### Alur 3 — Tes cepat (1 akun)

```cmd
python login.py --limit 1
```
*Hanya memproses 1 akun pertama di `akungsuite.txt`.*

---

## Troubleshooting

| Masalah | Solusi |
|---|---|
| `Chrome SEDANG BERJALAN...` | Tutup semua window Chrome, lalu jalankan ulang perintah |
| Akun tidak muncul di Chrome utama | Pastikan `push` dijalankan, Chrome utama tertutup saat itu, lalu baru buka |
| Halaman berhenti di ToS Workspace | Itu normal untuk akun baru — klik **setuju** di tab tersebut |
| Captcha tidak terselesaikan | Script sengaja berhenti — isi captcha manual, script tidak bisa lewati |
| Halaman tidak menemukan field password | Kemungkinan akun sudah login / halaman berbeda — tab dibiarkan terbuka untuk ditangani manual (status `stop-unknown`) |
| Akun lama hilang | Jangan khawatir — restore dari folder backup: `User Data\.backup-sync-*` |

---

## Struktur File

```
autologin-gsuite/
├── login.py          # Script login massal (profil kustom)
├── sync.py           # Pipeline: prepare / push / status (Chrome utama)
├── akungsuite.txt    # Daftar akun (email|password)
├── profiles/utama/   # Profil Chrome kustom (dibuat otomatis)
└── contoh/           # Referensi HTML halaman Google (untuk pengembangan)
```

---

## Kredit

- GitHub: [github.com/rzkyfhrzi21](https://github.com/rzkyfhrzi21)
- Instagram: [@rzkydev666](https://instagram.com/rzkydev666)
