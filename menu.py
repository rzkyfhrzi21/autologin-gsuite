import json
import os
import re
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
W = 64


def box(title, rows):
    """Panel bergaya 'Bercocok Tanam CLI': judul tengah, baris 'Label : value'."""
    label_w = max([len(l) for l, _ in rows] + [6])
    val_w = max([len(v) for v, _ in rows] + [8])
    inner = label_w + 3 + val_w
    bw = max(W, inner + 4)
    pad = max(0, bw - 2 - len(title))
    left = pad // 2
    print()
    print(f"╔{'═' * (bw - 2)}╗")
    print(f"║{' ' * left}{title}{' ' * (pad - left)}║")
    print(f"╠{'═' * (bw - 2)}╣")
    for label, value in rows:
        if value.startswith("✅") or value == "Ya" or value.replace(",", "").isdigit():
            value = f"{GREEN}{value}{RESET}"
        line = f"{CYAN}{label:<{label_w}}{RESET} : {value}"
        print(f"║  {line}{' ' * max(0, bw - 4 - len(line))}║")
    print(f"╚{'═' * (bw - 2)}╝")
    print()


def menu_row(text, color):
    """Baris menu dalam box dengan padding tepat (warna hanya di teks)."""
    content = f"  {color}{text}{RESET}"
    print(f"║{content}{' ' * (W - 2 - len(content))}║")


def ask(prompt=""):
    """input() yang tidak crash saat input tertutup (EOF/pipe habis)."""
    try:
        return input(prompt).strip()
    except EOFError:
        return None


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


def browser_proc_name():
    """Nama process browser utama sesuai config.json (default: chrome.exe)."""
    cfg = load_config()
    low = (cfg.get("chrome_main_path") or "").lower()
    if "brave-browser" in low:
        return "brave.exe"
    if "edge" in low:
        return "msedge.exe"
    return "chrome.exe"


def chrome_running():
    proc = browser_proc_name()
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {proc}", "/NH"],
            capture_output=True, text=True, timeout=10,
        )
        return proc in out.stdout
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


def profile_dirs(base):
    """Semua direktori profil browser: Default + Profile 1..N."""
    dirs = [base / "Default"]
    if base.exists():
        for d in sorted(base.glob("Profile *")):
            if re.fullmatch(r"Profile \d+", d.name):
                dirs.append(d)
    return dirs


def main_account_emails():
    """Email akun di avatar browser utama (account_info, semua profil).

    Fallback ke Secure Preferences: Chrome kadang baru menulis account_info
    ke file itu (mis. setelah akun pindah antar-profil)."""
    base = main_path()
    emails, seen = [], set()
    for pd in profile_dirs(base):
        for fname in ("Preferences", "Secure Preferences"):
            p = pd / fname
            if not p.exists():
                continue
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                ai = d.get("account_info", [])
                for a in ai if isinstance(ai, list) else []:
                    e = a.get("email") if isinstance(a, dict) else None
                    if e and e not in seen:
                        seen.add(e)
                        emails.append(e)
                break
            except Exception:
                continue
    return emails


def draw_table(accounts, synced):
    e = W - 2 - 15
    print(f"╔════╦{'═' * e}╦════════╗")
    print(f"║{'No':^4}║{'Email':^{e}}║{'Status':^8}║")
    print(f"╠════╬{'═' * e}╬════════╣")
    if not accounts:
        print(f"║{'':4}║{'akungsuite.txt kosong / tidak ada':^{e}}║{'':8}║")
    else:
        for i, (email, _) in enumerate(accounts, 1):
            status = f"{GREEN}✅ Sinkron{RESET}" if email in synced else f"{YELLOW}⏳ Belum{RESET}"
            print(f"║{i:^4}║  {email:<{e - 3}}║ {status:^8}║")
    print(f"╚════╩{'═' * e}╩════════╝")
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
    menu_row("MENU:", BOLD)
    menu_row("[1] Install semua yang diperlukan", GREEN)
    menu_row("[2] Otomasi tambah akun", GREEN)
    menu_row("[3] Bersihkan penyimpanan", YELLOW)
    menu_row("[4] Connect X.com (Grok) ke 9Router", GREEN)
    menu_row("[5] Pengaturan (lokasi browser utama)", CYAN)
    menu_row("[0] Keluar", RED)
    print(f"╚{'═' * (W - 2)}╝")
    print()
    return total, done, pending


BROWSER_PROFILES = [
    ("Chrome", Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data",
     [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
      r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"]),
    ("Brave", Path.home() / "AppData" / "Local" / "BraveSoftware" / "Brave-Browser" / "User Data",
     [r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
      r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe"]),
    ("Edge", Path.home() / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data",
     [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
      r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]),
]


def cmd_install():
    print()
    print(f"{BOLD}=== [1] INSTALL SEMUA YANG DIPERLUKAN ==={RESET}")
    print()
    print("  • Python:", sys.version.split()[0])
    detected = sorted({name for name, _, exes in BROWSER_PROFILES
                       if any(Path(p).exists() for p in exes)})
    if detected:
        print("  • Browser:", " / ".join(detected))
    else:
        print("  • Browser: ❌ Chrome/Brave/Edge tidak ditemukan — install salah satunya")
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
    print(f"{YELLOW}  ⚠️  Pastikan SEMUA window browser (termasuk browser utama) ditutup.{RESET}")
    if chrome_running():
        print(f"{RED}  ❌ Browser utama masih berjalan. Tutup dulu, lalu ulangi menu ini.{RESET}")
        ask("\n  Tekan Enter untuk kembali...")
        return
    if not ACCOUNTS_FILE.exists():
        print(f"{RED}  ❌ akungsuite.txt tidak ditemukan. Salin dari akungsuite.example.txt{RESET}")
        ask("\n  Tekan Enter untuk kembali...")
        return

    print(f"{CYAN}  [1/3] Menyiapkan profil otomasi (prepare)...{RESET}")
    r = subprocess.run([sys.executable, "-u", "sync.py", "prepare"], cwd=BASE)
    if r.returncode != 0:
        print(f"{RED}  ❌ Prepare gagal. Tekan Enter untuk kembali...{RESET}")
        ask()
        return

    print()
    print(f"{BOLD}{CYAN}  [2/3] Browser otomasi akan terbuka...{RESET}")
    print(f"{YELLOW}  → Isi captcha & klik setuju di setiap tab{RESET}")
    print(f"{YELLOW}  → Setelah SEMUA akun berhasil login, {BOLD}TUTUP WINDOW BROWSER OTOMASI{RESET}")
    print(f"{YELLOW}  → Akun akan {BOLD}otomatis tersimpan ke browser utama{RESET}")
    print()
    subprocess.run([sys.executable, "-u", "login.py"], cwd=BASE)

    print()
    print(f"{CYAN}  [3/3] Menyinkronkan ke browser utama (push)...{RESET}")
    r = subprocess.run([sys.executable, "-u", "sync.py", "push"], cwd=BASE)
    if r.returncode != 0:
        print(f"{RED}  ❌ Push gagal. Tekan Enter untuk kembali...{RESET}")
        ask()
        return

    print()
    print(f"{GREEN}  ✅ Selesai! Semua akun sudah tersimpan ke browser utama.{RESET}")
    print(f"{GREEN}  Buka browser utama untuk memeriksa daftar akun.{RESET}")
    ask("\n  Tekan Enter untuk kembali...")


def cmd_bersihkan():
    print()
    print(f"{BOLD}=== [3] BERSIHKAN PENYIMPANAN ==={RESET}")
    print()
    print(f"{YELLOW}  Ini menghapus profil Chrome otomasi (profiles/) yang berisi{RESET}")
    print(f"{YELLOW}  akun GSuite hasil login sebelumnya.{RESET}")
    print(f"{RED}  ⚠️  Jalankan ini HANYA setelah semua akun sudah sinkron{RESET}")
    print(f"{RED}  ke Chrome utama.{RESET}")
    print()
    ans = ask("  Yakin hapus? Ketik 'ya' untuk konfirmasi: ").strip().lower()
    if ans != "ya":
        print(f"{YELLOW}  Dibatalkan.{RESET}")
    elif CUSTOM_ROOT.exists():
        shutil.rmtree(CUSTOM_ROOT.parent)
        print(f"{GREEN}  ✅ Penyimpanan dibersihkan (profiles/ dihapus).{RESET}")
        print(f"{DIM}  Profil otomasi akan dibuat ulang otomatis saat menu 2.{RESET}")
    else:
        print(f"{GREEN}  ✅ Penyimpanan sudah bersih (profiles/ tidak ada).{RESET}")
    ask("\n  Tekan Enter untuk kembali...")


def pilih_browser_otomatis(cfg):
    os.system("cls" if os.name == "nt" else "clear")
    active = str(main_path()).lower()
    box(f"{BOLD}{CYAN}🔎 DETEKSI BROWSER{RESET}", [
        ("Pilih browser", "path User Data terisi otomatis"),
    ])
    for i, (name, default_path, exes) in enumerate(BROWSER_PROFILES, 1):
        exe_ok = any(Path(p).exists() for p in exes)
        data_ok = default_path.exists() and (default_path / "Local State").exists()
        mark = " ← aktif" if str(default_path).lower() == active else ""
        exe_txt = "✅ ditemukan" if exe_ok else "❌ tidak terinstall"
        data_txt = "✅ siap" if data_ok else "❌ belum pernah dipakai (buka browser dulu sekali)"
        print(f"  {BOLD}{GREEN}[{i}]{RESET} {name}{mark}")
        print(f"      executable : {exe_txt}")
        print(f"      User Data  : {data_txt}")
        print(f"      path       : {default_path}")
        print()
    choice = ask("  Pilih browser [1-3] / kosong untuk batal: ")
    if choice is None or not choice:
        print(f"{YELLOW}  ❌ Tidak diubah.{RESET}")
        return
    if not choice.isdigit() or not (1 <= int(choice) <= len(BROWSER_PROFILES)):
        print(f"{RED}  Pilihan tidak valid.{RESET}")
        return
    name, default_path, exes = BROWSER_PROFILES[int(choice) - 1]
    exe_ok = any(Path(p).exists() for p in exes)
    data_ok = default_path.exists() and (default_path / "Local State").exists()
    if not exe_ok:
        print(f"{RED}  ❌ {name} tidak terinstall — install dulu, lalu ulangi.{RESET}")
        return
    if not data_ok:
        print(f"{RED}  ❌ User Data {name} belum ada — buka {name} satu kali, tutup, lalu ulangi.{RESET}")
        return
    cfg["chrome_main_path"] = str(default_path)
    save_config(cfg)
    print(f"{GREEN}  ✅ Browser utama diset ke {name}.{RESET}")
    print(f"{DIM}  Path: {default_path}{RESET}")


def profile_emails(base, name):
    """Email akun login di satu profil (dari account_info Preferences / Secure Preferences)."""
    for fname in ("Preferences", "Secure Preferences"):
        p = Path(base) / name / fname
        if not p.exists():
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            ai = d.get("account_info", [])
            return [a.get("email") for a in ai
                    if isinstance(ai, list) and isinstance(a, dict) and a.get("email")]
        except Exception:
            continue
    return []


def cmd_connect9router():
    print()
    print(f"{BOLD}=== [4] CONNECT X.COM (GROK) KE 9ROUTER ==={RESET}")
    print()
    cfg = load_config()
    if not cfg.get("router9_url"):
        print(f"{RED}  ❌ 9Router belum dikonfigurasi.{RESET}")
        print()
        print(f"{YELLOW}  Buka config.json lalu isi:{RESET}")
        print(f"      \"router9_url\" : \"http://localhost:20128/\"")
        print(f"      \"router9_pass\": \"<password 9router, kosongkan bila tanpa password>\"")
        print()
        ask("  Tekan Enter untuk kembali...")
        return
    if chrome_running():
        print(f"{RED}  ❌ Browser utama masih berjalan. Tutup dulu, lalu ulangi menu ini.{RESET}")
        print(f"{YELLOW}  (Proses ini membuka profil kustom — snapshot profil utama — untuk memakai sesi GSuite.){RESET}")
        ask("\n  Tekan Enter untuk kembali...")
        return

    # 1) Pilih profil Chrome utama + lihat akun yang sudah login di dalamnya
    base = main_path()
    prof_list = []
    for pd in profile_dirs(base):
        if not pd.exists():
            continue
        prof_list.append(pd)
    if not prof_list:
        print(f"{RED}  ❌ Tidak ada profil Chrome ditemukan di:{RESET}")
        print(f"     {base}")
        ask("\n  Tekan Enter untuk kembali...")
        return

    print(f"{CYAN}  PROFIL CHROME (UTAMA) + AKUN YANG SUDAH LOGIN:{RESET}")
    for i, pd in enumerate(prof_list, 1):
        pe = profile_emails(base, pd.name)
        if pe:
            print(f"     {GREEN}[{i}]{RESET} {pd.name} — {len(pe)} akun")
            for e in pe:
                print(f"          - {e}")
        else:
            print(f"     {GREEN}[{i}]{RESET} {pd.name} — (tidak ada akun login tercatat)")
    print()
    ch = ask("  Pilih profil yang akan dipakai [1-%d] / kosong batal: " % len(prof_list))
    if ch is None or not ch:
        print(f"{YELLOW}  Dibatalkan.{RESET}")
        return
    if not ch.isdigit() or not (1 <= int(ch) <= len(prof_list)):
        print(f"{RED}  Pilihan tidak valid.{RESET}")
        return
    profile = prof_list[int(ch) - 1].name
    prof_emails = profile_emails(base, profile)

    # 2) Pilih akun dari profil itu (atau ketik manual / semua)
    email_arg = None
    if prof_emails:
        print()
        print(f"{CYAN}  AKUN LOGIN DI '{profile}':{RESET}")
        for i, e in enumerate(prof_emails, 1):
            print(f"     {GREEN}[{i}]{RESET} {e}")
        print(f"     {GREEN}[a]{RESET} Semua akun di profil ini")
        print(f"     {GREEN}[m]{RESET} Ketik email lain (pakai sesi Google/akungsuite)")
        print()
        ch = ask("  Pilih akun [1-%d]/a/m, kosong batal: " % len(prof_emails))
        if ch is None or not ch:
            print(f"{YELLOW}  Dibatalkan.{RESET}")
            return
        if ch.strip().lower() == "a":
            email_arg = None
        elif ch.strip().lower() == "m":
            em = ask("  Email target: ")
            if not em or not em.strip():
                print(f"{YELLOW}  Dibatalkan.{RESET}")
                return
            email_arg = em.strip()
        elif ch.isdigit() and (1 <= int(ch) <= len(prof_emails)):
            email_arg = prof_emails[int(ch) - 1]
        else:
            print(f"{RED}  Pilihan tidak valid.{RESET}")
            return
    else:
        em = ask(f"  Profil '{profile}' tanpa akun tercatat — ketik email target (pakai akungsuite.txt): ")
        if not em or not em.strip():
            print(f"{YELLOW}  Dibatalkan.{RESET}")
            return
        email_arg = em.strip()

    print()
    print(f"{CYAN}  Alur per akun GSuite:{RESET}")
    print(f"     1. Profil kustom disiapkan = snapshot profil '{profile}' (prepare otomatis)")
    print(f"     2. Buka dashboard 9Router -> klik Add -> modal device code")
    print(f"     3. Login accounts.x.ai via Google (sesi profile itu)")
    print(f"     4. Otorisasi device (Continue -> Allow) -> akun muncul di Connections")
    print(f"     5. Hasil dicatat di 9router_keys.txt")
    print(f"{YELLOW}  Catatan: akun X harus sudah terdaftar dengan email GSuite tersebut.{RESET}")
    if email_arg:
        print(f"\n  Target: {BOLD}{email_arg}{RESET} — profil: {BOLD}{profile}{RESET}")
    else:
        print(f"\n  Target: {BOLD}SEMUA akun di profil {profile}{RESET}")
    print()
    ans = ask("  Mulai connect? [y/N]: ")
    if ans is None or ans.strip().lower() != "y":
        print(f"{YELLOW}  Dibatalkan.{RESET}")
        return
    print()
    cmd = [sys.executable, "-u", "grok_router.py", "--profile", profile]
    if email_arg:
        cmd += ["--email", email_arg]
    subprocess.run(cmd, cwd=BASE)
    print()
    ask("  Tekan Enter untuk kembali...")


def cmd_pengaturan():
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        cfg = load_config()
        p = main_path()
        box(f"{BOLD}{CYAN}⚙️  PENGATURAN{RESET}", [
            ("🖥️  Lokasi browser utama", str(p)),
            ("✅ Path valid", "Ya" if p.exists() else "Tidak — periksa path"),
        ])
        print("╔" + "═" * (W - 2) + "╗")
        menu_row("[1] Ubah lokasi manual", GREEN)
        menu_row("[2] Deteksi otomatis browser", CYAN)
        menu_row("[9] Kembali ke menu utama", RED)
        print(f"╚{'═' * (W - 2)}╝")
        print()
        choice = ask("  Pilih [1 / 2 / 9]: ")
        if choice is None:
            return
        if choice == "1":
            print()
            while True:
                new_path = ask("  Masukkan path User Data browser utama\n"
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
                    print(f"{GREEN}  ✅ Path valid — Lokasi browser utama diperbarui.{RESET}")
                    break
                print(f"{RED}  ❌ Path tidak valid — 'Local State' / 'Default\\Preferences' "
                      f"tidak ditemukan di folder itu.{RESET}")
                print(f"{YELLOW}  Pastikan path menunjuk ke folder {BOLD}User Data{RESET} "
                      f"(Chrome/Brave/Edge), bukan ke chrome.exe/brave.exe.{RESET}")
                print()
            ask("  Tekan Enter untuk lanjut...")
        elif choice == "2":
            pilih_browser_otomatis(cfg)
            ask("  Tekan Enter untuk lanjut...")
        elif choice == "9":
            return
        else:
            print(f"{RED}  Pilihan tidak valid.{RESET}")
            ask("  Tekan Enter untuk lanjut...")


def main():
    while True:
        show_main_menu()
        choice = ask(f"  {BOLD}Pilih menu [0-5]: {RESET}")
        if choice is None:
            print(f"\n  {GREEN}Bye! 👋{RESET}")
            break
        if choice == "0":
            print(f"\n  {GREEN}Bye! 👋{RESET}")
            print(f"  Terima kasih sudah memakai tools ini 🙏")
            print(f"  {DIM}by rzkyfhrzi21 | @rzkydev666{RESET}\n")
            break
        elif choice == "1":
            cmd_install()
        elif choice == "2":
            cmd_otomasi()
        elif choice == "3":
            cmd_bersihkan()
        elif choice == "4":
            cmd_connect9router()
        elif choice == "5":
            cmd_pengaturan()
        else:
            print(f"\n  {RED}Pilihan tidak valid.{RESET}")
            ask("  Tekan Enter untuk lanjut...")


if __name__ == "__main__":
    main()
