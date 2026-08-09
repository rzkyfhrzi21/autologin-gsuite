import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if os.name == "nt":
    os.system("")

BASE = Path(__file__).parent
CONFIG_FILE = BASE / "config.json"
ACCOUNTS_FILE = BASE / "akungsuite.txt"
CUSTOM_ROOT = BASE / "profiles" / "utama"

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"

TITLE = f"{BOLD}{GREEN}🌱 AutoLogin GSuite CLI 🌱{RESET}"
CREDIT = f"{DIM}by rzkyfhrzi21 | @rzkydev666{RESET}"
W = 56


def box(title, rows):
    print()
    print(f"╔{'═' * (W - 2)}╗")
    pad = max(0, W - 2 - len(title))
    left = pad // 2
    print(f"║{' ' * left}{title}{' ' * (pad - left)}║")
    print(f"╠{'═' * (W - 2)}╣")
    for label, value in rows:
        line = f"{label}: {value}"
        print(f"║  {line}{' ' * max(0, W - 4 - len(line))}║")
    print(f"╚{'═' * (W - 2)}╝")
    print()


def load_config():
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_config(cfg):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def main_path():
    cfg = load_config()
    p = Path(cfg.get("chrome_main_path", ""))
    if p.exists():
        return p
    return Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data"


def chrome_running():
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq chrome.exe", "/NH"],
            capture_output=True, text=True, timeout=10,
        )
        return "chrome.exe" in out.stdout
    except Exception:
        return False


def load_accounts():
    accounts = []
    if ACCOUNTS_FILE.exists():
        for line in ACCOUNTS_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) >= 2:
                accounts.append((parts[0].strip(), parts[1].strip()))
    return accounts


def main_account_emails():
    p = main_path() / "Default" / "Preferences"
    if not p.exists():
        return []
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        ai = d.get("account_info", [])
        return [a.get("email") for a in ai if isinstance(a, dict) and a.get("email")]
    except Exception:
        return []


def draw_table(accounts, synced):
    print(f"╔════╦{'═' * 38}╦════════╗")
    print(f"║{'No':^4}║{'Email':^38}║{'Status':^8}║")
    print(f"╠════╬{'═' * 38}╬════════╣")
    if not accounts:
        print(f"║{'':4}║{'akungsuite.txt kosong / tidak ada':^38}║{'':8}║")
    else:
        for i, (email, _) in enumerate(accounts, 1):
            status = f"{GREEN}✅ Sinkron{RESET}" if email in synced else f"{YELLOW}⏳ Belum{RESET}"
            print(f"║{i:^4}║  {email:<36}║ {status:^8}║")
    print(f"╚════╩{'═' * 38}╩════════╝")
    print()


def show_main_menu():
    accounts = load_accounts()
    synced = main_account_emails()
    total = len(accounts)
    done = sum(1 for e, _ in accounts if e in synced)
    pending = total - done

    os.system("cls" if os.name == "nt" else "clear")
    box(TITLE + "  " + CREDIT, [
        ("📋 Total akun (akungsuite.txt)", str(total)),
        ("✅ Sudah sinkron ke Chrome utama", str(done)),
        ("⏳ Belum sinkron", str(pending)),
    ])
    print(f"{BOLD}Daftar akun yang bisa diotomasi:{RESET}")
    draw_table(accounts, synced)
    print("╔" + "═" * (W - 2) + "╗")
    print(f"║  {BOLD}MENU:{RESET}{' ' * (W - 10)}║")
    print(f"║  {BOLD}{GREEN}[1]{RESET} Install semua yang diperlukan{' ' * (W - 34)}║")
    print(f"║  {BOLD}{GREEN}[2]{RESET} Otomasi tambah akun{' ' * (W - 30)}║")
    print(f"║  {BOLD}{YELLOW}[3]{RESET} Bersihkan penyimpanan{' ' * (W - 31)}║")
    print(f"║  {BOLD}{CYAN}[4]{RESET} Pengaturan (lokasi Chrome utama){' ' * (W - 42)}║")
    print(f"║  {BOLD}{RED}[0]{RESET} Keluar{' ' * (W - 16)}║")
    print(f"╚{'═' * (W - 2)}╝")
    print()
    return total, done, pending


def cmd_install():
    print()
    print(f"{BOLD}=== [1] INSTALL SEMUA YANG DIPERLUKAN ==={RESET}")
    print()
    print("  • Python:", sys.version.split()[0])
    print("  • Chrome:", "✅ ditemukan" if (Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe").exists()
                                            or Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe").exists())
          else "❌ tidak ditemukan — pastikan Chrome terinstall")
    print()
    print(f"{CYAN}  Menginstall Playwright (Python)...{RESET}")
    r = subprocess.run([sys.executable, "-m", "pip", "install", "playwright"],
                       cwd=BASE)
    if r.returncode == 0:
        print(f"{GREEN}  ✅ Playwright terinstall.{RESET}")
    else:
        print(f"{RED}  ❌ Gagal install Playwright — cek koneksi internet & coba lagi.{RESET}")
    print(f"\n{GREEN}  Selesai. Tekan Enter untuk kembali...{RESET}")


def cmd_otomasi():
    print()
    print(f"{BOLD}=== [2] OTOMASI TAMBAH AKUN ==={RESET}")
    print()
    print(f"{YELLOW}  ⚠️  Pastikan SEMUA window Chrome (termasuk Chrome utama) ditutup.{RESET}")
    if chrome_running():
        print(f"{RED}  ❌ Chrome masih berjalan. Tutup dulu, lalu ulangi menu ini.{RESET}")
        input("\n  Tekan Enter untuk kembali...")
        return
    if not ACCOUNTS_FILE.exists():
        print(f"{RED}  ❌ akungsuite.txt tidak ditemukan. Salin dari akungsuite.example.txt{RESET}")
        input("\n  Tekan Enter untuk kembali...")
        return

    print(f"{CYAN}  [1/3] Menyiapkan profil otomasi (prepare)...{RESET}")
    r = subprocess.run([sys.executable, "-u", "sync.py", "prepare"], cwd=BASE)
    if r.returncode != 0:
        print(f"{RED}  ❌ Prepare gagal. Tekan Enter untuk kembali...{RESET}")
        input()
        return

    print()
    print(f"{BOLD}{CYAN}  [2/3] Chrome otomasi akan terbuka...{RESET}")
    print(f"{YELLOW}  → Isi captcha & klik setuju di setiap tab{RESET}")
    print(f"{YELLOW}  → Setelah SEMUA akun berhasil login, {BOLD}TUTUP WINDOW CHROME OTOMASI{RESET}")
    print(f"{YELLOW}  → Akun akan {BOLD}otomatis tersimpan ke Chrome utama{RESET}")
    print()
    subprocess.run([sys.executable, "-u", "login.py"], cwd=BASE)

    print()
    print(f"{CYAN}  [3/3] Menyinkronkan ke Chrome utama (push)...{RESET}")
    r = subprocess.run([sys.executable, "-u", "sync.py", "push"], cwd=BASE)
    if r.returncode != 0:
        print(f"{RED}  ❌ Push gagal. Tekan Enter untuk kembali...{RESET}")
        input()
        return

    print()
    print(f"{GREEN}  ✅ Selesai! Semua akun sudah tersimpan ke Chrome utama.{RESET}")
    print(f"{GREEN}  Buka Chrome utama untuk memeriksa daftar akun.{RESET}")
    input("\n  Tekan Enter untuk kembali...")


def cmd_bersihkan():
    print()
    print(f"{BOLD}=== [3] BERSIHKAN PENYIMPANAN ==={RESET}")
    print()
    print(f"{YELLOW}  Ini menghapus profil Chrome otomasi (profiles/) yang berisi{RESET}")
    print(f"{YELLOW}  akun GSuite hasil login sebelumnya.{RESET}")
    print(f"{RED}  ⚠️  Jalankan ini HANYA setelah semua akun sudah sinkron{RESET}")
    print(f"{RED}  ke Chrome utama.{RESET}")
    print()
    ans = input("  Yakin hapus? Ketik 'ya' untuk konfirmasi: ").strip().lower()
    if ans != "ya":
        print(f"{YELLOW}  Dibatalkan.{RESET}")
    elif CUSTOM_ROOT.exists():
        shutil.rmtree(CUSTOM_ROOT.parent)
        print(f"{GREEN}  ✅ Penyimpanan dibersihkan (profiles/ dihapus).{RESET}")
        print(f"{DIM}  Profil otomasi akan dibuat ulang otomatis saat menu 2.{RESET}")
    else:
        print(f"{GREEN}  ✅ Penyimpanan sudah bersih (profiles/ tidak ada).{RESET}")
    input("\n  Tekan Enter untuk kembali...")


def cmd_pengaturan():
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        cfg = load_config()
        p = main_path()
        box(f"{BOLD}{CYAN}⚙️  PENGATURAN{RESET}", [
            ("🖥️  Lokasi Chrome utama", str(p)),
            ("✅ Path valid", "Ya" if p.exists() else "Tidak — periksa path"),
        ])
        print("╔" + "═" * (W - 2) + "╗")
        print(f"║  {BOLD}{GREEN}[1]{RESET} Ubah lokasi Chrome utama{' ' * (W - 32)}║")
        print(f"║  {BOLD}{RED}[9]{RESET} Kembali ke menu utama{' ' * (W - 30)}║")
        print(f"╚{'═' * (W - 2)}╝")
        print()
        choice = input("  Pilih [1 / 9]: ").strip()
        if choice == "1":
            print()
            while True:
                new_path = input("  Masukkan path User Data Chrome utama\n"
                                 "  (kosong untuk batal): ").strip().strip('"')
                if not new_path:
                    print(f"{YELLOW}  ❌ Tidak diubah — kembali ke menu pengaturan.{RESET}")
                    break
                p = Path(new_path)
                local_state = p / "Local State"
                prefs = p / "Default" / "Preferences"
                if p.exists() and (local_state.exists() or prefs.exists()):
                    cfg["chrome_main_path"] = str(p)
                    save_config(cfg)
                    print(f"{GREEN}  ✅ Path valid — Lokasi Chrome utama diperbarui.{RESET}")
                    break
                print(f"{RED}  ❌ Path tidak valid — 'Local State' / 'Default\\Preferences' "
                      f"tidak ditemukan di folder itu.{RESET}")
                print(f"{YELLOW}  Pastikan path menunjuk ke folder {BOLD}User Data{RESET} "
                      f"Chrome, bukan ke chrome.exe.{RESET}")
                print()
            input("  Tekan Enter untuk lanjut...")
        elif choice == "9":
            return
        else:
            print(f"{RED}  Pilihan tidak valid.{RESET}")
            input("  Tekan Enter untuk lanjut...")


def main():
    while True:
        show_main_menu()
        choice = input(f"  {BOLD}Pilih menu [0-4]: {RESET}").strip()
        if choice == "0":
            print(f"\n  {GREEN}Bye! 👋{RESET}\n")
            break
        elif choice == "1":
            cmd_install()
        elif choice == "2":
            cmd_otomasi()
        elif choice == "3":
            cmd_bersihkan()
        elif choice == "4":
            cmd_pengaturan()
        else:
            print(f"\n  {RED}Pilihan tidak valid.{RESET}")
            input("  Tekan Enter untuk lanjut...")


if __name__ == "__main__":
    main()
