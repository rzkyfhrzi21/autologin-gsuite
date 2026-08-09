# AutoLogin GSuite

Alat otomatis untuk login banyak akun Google Workspace (GSuite) sekaligus ke satu profil Chrome, tanpa kehilangan akun yang sudah ada.

Cara kerja: login dilakukan di **profil Chrome terpisah** (profil kustom) karena Chrome modern memblokir otomasi di profil utama, lalu hasilnya disinkronkan kembali ke Chrome utama yang biasa kamu pakai.

> Dibuat & dikembangkan oleh [**rzkyfhrzi21**](https://github.com/rzkyfhrzi21) — Instagram: [**@rzkydev666**](https://instagram.com/rzkydev666)

---

## Fitur

| Fitur | Keterangan |
|---|---|
| Menu CLI interaktif | Jalankan `python menu.py` — semua fitur dalam satu menu bernomor, lengkap dengan tabel status akun |
| Login massal otomatis | Email & password terisi otomatis dari `akungsuite.txt`, 1 tab per akun |
| Auto-sinkron ke Chrome utama | Setelah login selesai di Chrome otomasi, **cukup tutup window** — akun otomatis tersimpan ke Chrome utama |
| Anti-deteksi otomasi | Stealth script (webdriver spoof, plugin, language) + ketik dengan delay manusia |
| Deteksi captcha otomatis | Saat halaman captcha muncul: password kedua terisi otomatis, script **berhenti aman** — kamu tinggal isi captcha & klik setuju manual |
| Deteksi ToS/consent | Halaman "Workspace Terms of Service" dideteksi, tab dibiarkan untuk persetujuan manual |
| Akun lama tidak hilang | Pipeline `prepare → push` selalu menyinkronkan penuh, jadi akun yang sudah ada **tidak pernah terhapus** |
| Backup otomatis | Setiap file yang akan diubah di-backup dulu (folder `.backup-sync-*`) |
| Pengaman Chrome | Script menolak berjalan jika Chrome masih terbuka (mencegah file tertimpa dari memori) |
| Mode tes | `python login.py --limit N` untuk mencoba hanya N akun pertama |

---

## Kebutuhan (setiap perangkat baru)

1. **Python 3.11+** — unduh di [python.org](https://www.python.org/downloads/) (centang *Add to PATH* saat install)
2. **Google Chrome** — [google.com/chrome](https://www.google.com/chrome/) (versi apa pun, terbaru disarankan)
3. **Playwright (Python)** — bisa install manual:
   ```cmd
   pip install playwright
   ```
   atau otomatis lewat menu `[1] Install semua yang diperlukan`.

Tidak perlu `playwright install chromium` — script memakai Chrome yang sudah terpasang.

---

## Setup Awal (sekali per perangkat)

1. **Cek path Chrome** di `login.py` (variabel `CHROME_PATH`):
   ```python
   CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
   ```
   Sesuaikan jika lokasi Chrome kamu berbeda.

2. **Set lokasi Chrome utama** — jalankan `python menu.py`, pilih menu `[4] Pengaturan` → `[1] Ubah lokasi Chrome utama`, masukkan path User Data Chrome (contoh: `C:\Users\rizky\AppData\Local\Google\Chrome\User Data`). Disimpan di `config.json`.
   - Path **divalidasi otomatis** (memeriksa `Local State` / `Default\Preferences`) — jika salah, muncul pesan error dan kamu bisa input ulang
   - Enter kosong = batal, lokasi lama tetap dipakai
   - Path harus menunjuk ke folder **User Data** (bukan `chrome.exe`)

3. **Isi daftar akun** di `akungsuite.txt` (format `email|password`, satu per baris):
   ```
   # AKUN GSUITE UNTUK AUTO LOGIN
   # Format: email|password (satu akun per baris)
   # Baris yang diawali # diabaikan (komentar)

   akun1@perusahaan.com|password1
   akun2@perusahaan.com|password2
   ```
   Salin dari `akungsuite.example.txt` jika belum ada.

4. **Buka Chrome sekali**, login manual akun utama kamu (misal akun pribadi), lalu **tutup Chrome** — profil utama harus dalam keadaan berisi akun yang sudah ada sebelum mulai.

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
| `[4]` | **Pengaturan** — ubah lokasi Chrome utama (validasi otomatis; kembali ke menu utama: `[9]`) |
| `[0]` | **Keluar** |

### Alur lengkap menu 2 — Otomasi tambah akun

1. Pastikan semua Chrome (termasuk Chrome utama) **tertutup**
2. Pilih `[2]` → script menyiapkan profil otomasi & membuka Chrome otomasi
3. Isi **captcha** & klik **setuju** di setiap tab (script berhenti aman di sana)
4. Setelah **semua akun berhasil login**, **tutup window Chrome otomasi**
5. Script otomatis menyinkronkan (push) ke Chrome utama
6. Buka Chrome utama → semua akun sudah ada di avatar ✅

> **⚠️ Aturan emas: Chrome harus TERTUTUP saat script menyiapkan/menyinkronkan profil** (script otomatis menolak jika Chrome masih jalan).

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
| Path lokasi Chrome utama ditolak | Path harus folder **User Data** (berisi `Local State`), bukan `chrome.exe` — contoh benar: `C:\Users\rizky\AppData\Local\Google\Chrome\User Data` |
| Akun tidak muncul di Chrome utama | Pastikan `push` dijalankan, Chrome utama tertutup saat itu, lalu baru buka |
| Halaman berhenti di ToS Workspace | Itu normal untuk akun baru — klik **setuju** di tab tersebut |
| Captcha tidak terselesaikan | Script sengaja berhenti — isi captcha manual, script tidak bisa lewati |
| Halaman tidak menemukan field password | Kemungkinan akun sudah login / halaman berbeda — tab dibiarkan terbuka untuk ditangani manual (status `stop-unknown`) |
| Akun lama hilang | Jangan khawatir — restore dari folder backup: `User Data\.backup-sync-*` |

---

## Struktur File

```
autologin-gsuite/
├── menu.py            # Menu CLI utama (python menu.py)
├── login.py           # Script login massal (profil kustom)
├── sync.py            # Pipeline: prepare / push / status (Chrome utama)
├── akungsuite.txt     # Daftar akun (email|password) — TIDAK ikut GitHub
├── akungsuite.example.txt  # Template daftar akun (aman di-push)
├── config.json        # Konfigurasi lokal: lokasi Chrome utama — TIDAK ikut GitHub
├── config.example.json      # Template konfigurasi (aman di-push)
├── profiles/utama/    # Profil Chrome kustom (dibuat otomatis saat menu 2)
└── contoh/            # Referensi HTML halaman Google (untuk pengembangan)
```

---

## Kredit

- GitHub: [github.com/rzkyfhrzi21](https://github.com/rzkyfhrzi21)
- Instagram: [@rzkydev666](https://instagram.com/rzkydev666)
