import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CUSTOM_ROOT = Path(__file__).parent / "profiles" / "utama"
CONFIG_FILE = Path(__file__).parent / "config.json"

# Semua file penentu sesi/akun Google, relatif terhadap root user-data.
SYNC_RELS = [
    "Local State",
    "Default/Preferences",
    "Default/Secure Preferences",
    "Default/Network/Cookies",
    "Default/Network/Cookies-journal",
    "Default/Local Storage/leveldb",
    "Default/Web Data",
    "Default/Web Data-journal",
    "Default/Login Data",
    "Default/Login Data-journal",
]


def get_main_root():
    """Lokasi User Data Chrome utama — dibaca dari config.json (bisa diubah di menu 4)."""
    if CONFIG_FILE.exists():
        try:
            cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            p = Path(cfg.get("chrome_main_path", ""))
            if p and p.exists():
                return p
        except Exception:
            pass
    # Default: C:\Users\<user>\AppData\Local\Google\Chrome\User Data
    default = Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data"
    if CONFIG_FILE.exists():
        try:
            cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}
        cfg["chrome_main_path"] = str(default)
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return default


BROWSER_PROC = {"chrome": "chrome.exe", "brave": "brave.exe", "edge": "msedge.exe"}
BROWSER_LABEL = {"chrome": "Chrome", "brave": "Brave", "edge": "Edge"}


def main_browser_name():
    """Nama browser utama sesuai lokasi User Data di config.json (default: Chrome)."""
    if CONFIG_FILE.exists():
        try:
            cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            low = (cfg.get("chrome_main_path") or "").lower()
            if "brave-browser" in low:
                return "brave"
            if "edge" in low:
                return "edge"
        except Exception:
            pass
    return "chrome"


def browser_label():
    return BROWSER_LABEL[main_browser_name()]


def chrome_running():
    proc = BROWSER_PROC[main_browser_name()]
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {proc}", "/NH"],
            capture_output=True, text=True, timeout=10,
        )
        return proc in out.stdout
    except Exception:
        return False


def die_if_chrome_open():
    b = browser_label()
    if chrome_running():
        print(f"⛔ {b} SEDANG BERJALAN. Tutup SEMUA window {b} dulu,")
        print("   lalu jalankan ulang perintah ini. File profil terkunci &")
        print(f"   {b} bisa menimpa perubahan kita dari memori.")
        sys.exit(1)


def copy_item(src, dst):
    if not src.exists():
        print(f"  - skip (sumber tidak ada): {src.name}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    backup_dir = dst.parent / f".backup-sync-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    if dst.exists():
        if dst.is_dir():
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            shutil.copytree(dst, backup_dir)
        else:
            shutil.copy2(dst, backup_dir)
        print(f"  backup: {dst}")
    if src.is_dir():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)
    print(f"  ✓ disalin: {src.name}")


def profile_dirs(base):
    """Semua direktori profil Chrome: Default + Profile 1..N."""
    dirs = [base / "Default"]
    if base.exists():
        for d in sorted(base.glob("Profile *")):
            if re.fullmatch(r"Profile \d+", d.name):
                dirs.append(d)
    return dirs


def emails_in_profile(pd):
    p = pd / "Preferences"
    if not p.exists():
        return []
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        ai = d.get("account_info", [])
        return [a.get("email") for a in ai
                if isinstance(ai, list) and isinstance(a, dict) and a.get("email")]
    except Exception:
        return []


def account_emails(base):
    """Email akun dari SEMUA profil browser utama (Default + Profile N)."""
    emails, seen = [], set()
    for pd in profile_dirs(base):
        for e in emails_in_profile(pd):
            if e not in seen:
                seen.add(e)
                emails.append(e)
    return emails


def main_account_emails():
    """Email akun yang tercatat di avatar browser utama (account_info, semua profil)."""
    return account_emails(get_main_root())


def show_accounts(base, label):
    emails = account_emails(base)
    if not any(pd.exists() for pd in profile_dirs(base)):
        print(f"  [{label}] profil tidak ditemukan")
    elif emails:
        print(f"  [{label}] akun di avatar ({len(emails)}): {emails}")
        for pd in profile_dirs(base):
            pe = emails_in_profile(pd)
            if pe:
                print(f"  [{label}]  • {pd.name}: {pe}")
    else:
        print(f"  [{label}] (kosong — tidak ada akun tercatat di profil mana pun)")


def cmd_prepare():
    """Snapshot profil UTAMA -> KUSTOM. Jalankan SEBELUM login akun baru."""
    die_if_chrome_open()
    main_root = get_main_root()
    print("=== PREPARE: salin profil utama -> profil kustom ===")
    print("Lokasi browser utama:", main_root)
    if not (main_root / "Default").exists():
        print("Profil utama tidak ditemukan:", main_root)
        print("Cek lokasi di menu Pengaturan (menu 4).")
        sys.exit(1)
    for rel in SYNC_RELS:
        copy_item(main_root / rel.replace("/", "\\"), CUSTOM_ROOT / rel.replace("/", "\\"))
    print("\nSelesai. Profil kustom kini = snapshot utama terbaru.")
    print("Lanjutkan: jalankan script login di profil kustom, lalu 'push'.")
    show_accounts(CUSTOM_ROOT, "kustom")


def cmd_push():
    """Kirim hasil login dari profil KUSTOM -> UTAMA. Jalankan SETELAH login."""
    die_if_chrome_open()
    main_root = get_main_root()
    print("=== PUSH: salin profil kustom -> profil utama ===")
    print("Lokasi browser utama:", main_root)
    if not (CUSTOM_ROOT / "Default").exists():
        print("Profil kustom tidak ditemukan:", CUSTOM_ROOT)
        print("Jalankan 'prepare' dulu (menu 2 / sync.py prepare).")
        sys.exit(1)
    for rel in SYNC_RELS:
        copy_item(CUSTOM_ROOT / rel.replace("/", "\\"), main_root / rel.replace("/", "\\"))
    print("\nSelesai. Akun dari profil kustom dipindah ke utama.")
    print(f"Buka {browser_label()} utama — akun lama tetap ada, akun baru bertambah.")
    show_accounts(main_root, "utama")


def cmd_status():
    print("=== STATUS ===")
    print("Lokasi browser utama:", get_main_root())
    show_accounts(get_main_root(), "utama")
    show_accounts(CUSTOM_ROOT, "kustom")
    print(f"{browser_label()} berjalan: {chrome_running()}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    {"prepare": cmd_prepare, "push": cmd_push, "status": cmd_status}.get(cmd, cmd_status)()
