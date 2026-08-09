# AutoLogin GSuite

Alat otomatis untuk login banyak akun Google Workspace (GSuite) sekaligus ke satu profil Chrome, tanpa kehilangan akun yang sudah ada.

Cara kerja: login dilakukan di **profil Chrome terpisah** (profil kustom) karena Chrome modern memblokir otomasi di profil utama, lalu hasilnya disinkronkan kembali ke Chrome utama yang biasa kamu pakai.

> Dibuat & dikembangkan oleh [**rzkyfhrzi21**](https://github.com/rzkyfhrzi21) — Instagram: [**@rzkydev666**](https://instagram.com/rzkydev666)

---

## Fitur

| Fitur | Keterangan |
|---|---|
| Menu CLI interaktif | Jalankan `python menu.py` — semua fitur dalam satu menu bernomor, lengkap dengan tabel status akun |
| Multi-browser | Chrome, **Brave**, dan Edge didukung — executable dideteksi otomatis dari lokasi User Data yang dipilih di pengaturan |
| Login massal otomatis | Email & password terisi otomatis dari `akungsuite.txt`, 1 tab per akun |
| Auto-sinkron ke Chrome utama | Setelah login selesai di Chrome otomasi, **cukup tutup window** — akun otomatis tersimpan ke Chrome utama |
| Anti-deteksi otomasi | Stealth script (webdriver spoof, plugin, language) + ketik dengan delay manusia |
| Deteksi captcha otomatis | Saat halaman captcha muncul: password kedua terisi otomatis, script **berhenti aman** — kamu tinggal isi captcha & klik setuju manual |
| Deteksi ToS/consent | Halaman "Workspace Terms of Service" dideteksi, tab dibiarkan untuk persetujuan manual |
| Akun lama tidak hilang | Pipeline `prepare → push` selalu menyinkronkan penuh, jadi akun yang sudah ada **tidak pernah terhapus** |
| Backup otomatis | Setiap file yang akan diubah di-backup dulu (folder `.backup-sync-*`) |
| Pengaman Chrome | Script menolak berjalan jika Chrome masih terbuka (mencegah file tertimpa dari memori) |
| Mode tes | `python login.py --limit N` untuk mencoba hanya N akun pertama |
| Connect X.com (Grok) ke 9Router | Login X.com via Google (sesi GSuite) → device flow 9router provider `grok-cli` (dashboard → Add → modal → Continue → Allow) → hasil di `9router_keys.txt` |

---

## Kebutuhan (setiap perangkat baru)

1. **Python 3.11+** — unduh di [python.org](https://www.python.org/downloads/) (centang *Add to PATH* saat install)
2. **Browser Chromium (salah satu):**
   - [Google Chrome](https://www.google.com/chrome/)
   - [Brave](https://brave.com/download/)
   - [Microsoft Edge](https://www.microsoft.com/edge) (bawaan Windows)
3. **Playwright (Python)** — bisa install manual:
   ```cmd
   pip install playwright
   ```
   atau otomatis lewat menu `[1] Install semua yang diperlukan`.

Tidak perlu `playwright install chromium` — script memakai browser Chromium yang sudah terpasang.

---

## Setup Awal (sekali per perangkat)

1. **Executable browser dideteksi otomatis** (mengikuti browser di langkah 2). Tidak perlu mengubah kode manual.

2. **Set lokasi browser utama** — jalankan `python menu.py`, pilih menu `[4] Pengaturan`:
   - `[1] Ubah lokasi manual` — ketik path User Data browser (contoh di bawah)
   - `[2] Deteksi otomatis browser` — pilih Chrome / Brave / Edge, path User Data terisi otomatis + divalidasi
   - Chrome: `C:\Users\rizky\AppData\Local\Google\Chrome\User Data`
   - Brave: `C:\Users\rizky\AppData\Local\BraveSoftware\Brave-Browser\User Data`
   - Edge: `C:\Users\rizky\AppData\Local\Microsoft\Edge\User Data`

   Disimpan di `config.json`.
   - Path **divalidasi otomatis** (memeriksa `Local State` / `Default\Preferences`) — jika salah, muncul pesan error dan kamu bisa input ulang
   - Enter kosong = batal, lokasi lama tetap dipakai
   - Path harus menunjuk ke folder **User Data** (bukan `chrome.exe` / `brave.exe`)

3. **Konfigurasi 9Router** (untuk menu `[4]`) di `config.json`:
   ```json
   {
     "chrome_main_path": "C:\\Users\\rizky\\AppData\\Local\\Google\\Chrome\\User Data",
     "router9_url": "http://localhost:20128/",
     "router9_pass": "<password 9router kamu>"
   }
   ```
   `router9_url` = URL instance 9router lokal, `router9_pass` = password dashboard (dipakai `POST /api/auth/login`).

4. **Isi daftar akun** di `akungsuite.txt` (format `email|password`, satu per baris):
   ```
   # AKUN GSUITE UNTUK AUTO LOGIN
   # Format: email|password (satu akun per baris)
   # Baris yang diawali # diabaikan (komentar)

   akun1@perusahaan.com|password1
   akun2@perusahaan.com|password2
   ```
   Salin dari `akungsuite.example.txt` jika belum ada.

5. **Buka Chrome sekali**, login manual akun utama kamu (misal akun pribadi), lalu **tutup Chrome** — profil utama harus dalam keadaan berisi akun yang sudah ada sebelum mulai.

---

## Penggunaan (Menu CLI)

Jalankan di CMD:

```cmd
python menu.py
```

Menampilkan: nama project + credit, statistik akun (total / sudah sinkron / belum), tabel daftar akun, dan menu:

| Menu | Fungsi |
|---|---|
| `[1]` | **Install semua yang diperlukan** — cek Python & Chrome, install Playwright |
| `[2]` | **Otomasi tambah akun** — siapkan profil → buka Chrome otomasi → isi captcha & setuju manual → **tutup window Chrome otomasi** → otomatis sinkron ke Chrome utama |
| `[3]` | **Bersihkan penyimpanan** — hapus profil Chrome otomasi (pakai setelah semua akun sinkron) |
| `[4]` | **Connect X.com (Grok) ke 9Router** — login X.com via Google (sesi GSuite) → cookie sso → device flow 9router `grok-cli` → hasil di `9router_keys.txt` |
| `[5]` | **Pengaturan** — ubah lokasi browser utama manual atau **deteksi otomatis** (pilih Chrome/Brave/Edge; kembali ke menu utama: `[9]`) |
| `[0]` | **Keluar** |

### Alur lengkap menu 4 — Connect X.com (Grok) ke 9Router

> ⚠️ **BELUM SELESAI** — fitur ini masih dalam pengembangan dan belum lolos tes end-to-end
> (Cloudflare memblokir accounts.x.ai di profil kustom otomasi; klik "Login with Google"
> belum berhasil membuka popup OAuth). Jangan gunakan untuk produksi.

1. Pastikan **9Router sudah terkonfigurasi** di `config.json` (`router9_url`, `router9_pass`) — password dashboard 9router kamu
2. Pastikan semua window browser (termasuk browser utama) **tertutup**
3. Pilih `[4]` → script membuka browser utama sendiri dan untuk **setiap akun GSuite** di `akungsuite.txt`:
   - Login **X.com** via Google — akun GSuite dipilih otomatis dari sesi Google yang ada (email/password terisi otomatis jika perlu)
   - Buka **grok.com** untuk membangun sesi X/Grok (klik `Continue with X` bila perlu)
   - Kumpulkan cookie `sso` / `sso-rw` / `x-userid` → inject ke halaman otorisasi 9router
   - Klik `Continue` → `Allow` → 9router di-poll sampai berhasil
4. Hasil tiap akun dicatat di **`9router_keys.txt`** (format `email|status|tanggal`)

> **Catatan:** akun X harus sudah terdaftar dengan email GSuite tersebut — email temp tidak bisa (pengalaman dari proyek sebelumnya). Jika ada captcha/verifikasi Google, selesaikan manual di tab yang terbuka.

### Alur lengkap menu 2 — Otomasi tambah akun

1. Pastikan semua window browser (termasuk browser utama) **tertutup**
2. Pilih `[2]` → script menyiapkan profil otomasi & membuka browser otomasi
3. Isi **captcha** & klik **setuju** di setiap tab (script berhenti aman di sana)
4. Setelah **semua akun berhasil login**, **tutup window browser otomasi**
5. Script otomatis menyinkronkan (push) ke browser utama
6. Buka browser utama → semua akun sudah ada di avatar ✅

> **⚠️ Aturan emas: browser utama harus TERTUTUP saat script menyiapkan/menyinkronkan profil** (script otomatis menolak jika masih jalan).

---

## Penggunaan (Perintah Langsung)

### Alur 1 — Tambah akun baru

```cmd
python sync.py prepare
```
*Menyalin profil utama → profil kustom (snapshot terbaru, akun lama ikut terbawa).*

```cmd
python login.py
```
*Membuka browser kustom, mengisi email + password semua akun di `akungsuite.txt`. Berhenti otomatis di halaman captcha / ToS. Kamu selesaikan manual: isi captcha → klik Next → setuju, di tiap tab. Setelah selesai, **tutup browser**.*

```cmd
python sync.py push
```
*Menyalin hasil login dari profil kustom → profil utama. Akun lama tetap, akun baru bertambah.*

**Buka browser utama → semua akun sudah ada di avatar.**

### Alur 2 — Cek status

```cmd
python sync.py status
```
*Menampilkan daftar akun di profil utama & kustom, dan status browser.*

### Alur 3 — Tes cepat (1 akun)

```cmd
python login.py --limit 1
```
*Hanya memproses 1 akun pertama di `akungsuite.txt`.*

### Alur 4 — Connect X.com ke 9Router

```cmd
python grok_router.py
```
*Login X.com via Google untuk tiap akun GSuite, ambil cookie sso, lalu device flow 9router (provider `grok-cli`). Hasil dicatat di `9router_keys.txt`.*

```cmd
python grok_router.py --limit 1
```
*Hanya memproses 1 akun pertama (mode tes).*

---

## Troubleshooting

| Masalah | Solusi |
|---|---|
| `Chrome SEDANG BERJALAN...` | Tutup semua window browser (Chrome/Brave/Edge), lalu jalankan ulang perintah |
| Path lokasi browser utama ditolak | Path harus folder **User Data** (berisi `Local State`), bukan `chrome.exe` — contoh benar: `C:\Users\rizky\AppData\Local\Google\Chrome\User Data` (Brave: `...\BraveSoftware\Brave-Browser\User Data`) |
| Akun tidak muncul di browser utama | Pastikan `push` dijalankan, browser utama tertutup saat itu, lalu baru buka |
| Halaman berhenti di ToS Workspace | Itu normal untuk akun baru — klik **setuju** di tab tersebut |
| Captcha tidak terselesaikan | Script sengaja berhenti — isi captcha manual, script tidak bisa lewati |
| Halaman tidak menemukan field password | Kemungkinan akun sudah login / halaman berbeda — tab dibiarkan terbuka untuk ditangani manual (status `stop-unknown`) |
| Akun lama hilang | Jangan khawatir — restore dari folder backup: `User Data\.backup-sync-*` |

---

## Struktur File

```
autologin-gsuite/
├── menu.py            # Menu CLI utama (python menu.py)
├── login.py           # Script login massal (profil kustom, multi-browser)
├── sync.py            # Pipeline: prepare / push / status (browser utama)
├── grok_router.py     # Connect X.com (Grok) ke 9Router via sesi GSuite
├── akungsuite.txt     # Daftar akun (email|password) — TIDAK ikut GitHub
├── akungsuite.example.txt  # Template daftar akun (aman di-push)
├── config.json        # Konfigurasi lokal: lokasi browser + 9Router — TIDAK ikut GitHub
├── config.example.json      # Template konfigurasi (aman di-push)
├── 9router_keys.txt   # Hasil connect X.com ke 9Router — TIDAK ikut GitHub
├── profiles/utama/    # Profil browser kustom (dibuat otomatis saat menu 2)
└── contoh/            # Referensi HTML halaman Google (untuk pengembangan)
```

---

## Kredit

- GitHub: [github.com/rzkyfhrzi21](https://github.com/rzkyfhrzi21)
- Instagram: [@rzkydev666](https://instagram.com/rzkydev666)
