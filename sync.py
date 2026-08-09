import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CUSTOM_ROOT = Path(__file__).parent / "profiles" / "utama"
MAIN_ROOT = Path(r"C:\Users\rizky\AppData\Local\Google\Chrome\User Data")

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


def chrome_running():
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq chrome.exe", "/NH"],
            capture_output=True, text=True, timeout=10,
        )
        return "chrome.exe" in out.stdout
    except Exception:
        return False


def die_if_chrome_open():
    if chrome_running():
        print("⛔ Chrome SEDANG BERJALAN. Tutup SEMUA window Chrome dulu,")
        print("   lalu jalankan ulang perintah ini. File profil terkunci &")
        print("   Chrome bisa menimpa perubahan kita dari memori.")
        sys.exit(1)


def copy_item(src, dst):
    if not src.exists():
        print(f"  - skip (sumber tidak ada): {src.name}")
        return
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


def show_accounts(base, label):
    p = base / "Default" / "Preferences"
    if not p.exists():
        print(f"  [{label}] Preferences tidak ada")
        return
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        ai = d.get("account_info", [])
        emails = [a.get("email") for a in ai] if isinstance(ai, list) else []
        print(f"  [{label}] akun di avatar: {emails if emails else '(kosong)'}")
    except Exception as e:
        print(f"  [{label}] gagal baca: {e}")


def cmd_prepare():
    """Snapshot profil UTAMA -> KUSTOM. Jalankan SEBELUM login akun baru."""
    die_if_chrome_open()
    print("=== PREPARE: salin profil utama -> profil kustom ===")
    if not (MAIN_ROOT / "Default").exists():
        print("Profil utama tidak ditemukan:", MAIN_ROOT)
        sys.exit(1)
    for rel in SYNC_RELS:
        copy_item(MAIN_ROOT / rel.replace("/", "\\"), CUSTOM_ROOT / rel.replace("/", "\\"))
    print("\nSelesai. Profil kustom kini = snapshot utama terbaru.")
    print("Lanjutkan: jalankan script login di profil kustom, lalu 'push'.")
    show_accounts(CUSTOM_ROOT, "kustom")


def cmd_push():
    """Kirim hasil login dari profil KUSTOM -> UTAMA. Jalankan SETELAH login."""
    die_if_chrome_open()
    print("=== PUSH: salin profil kustom -> profil utama ===")
    if not (CUSTOM_ROOT / "Default").exists():
        print("Profil kustom tidak ditemukan:", CUSTOM_ROOT)
        sys.exit(1)
    for rel in SYNC_RELS:
        copy_item(CUSTOM_ROOT / rel.replace("/", "\\"), MAIN_ROOT / rel.replace("/", "\\"))
    print("\nSelesai. Akun dari profil kustom dipindah ke utama.")
    print("Buka Chrome utama — akun lama tetap ada, akun baru bertambah.")
    show_accounts(MAIN_ROOT, "utama")


def cmd_status():
    print("=== STATUS ===")
    show_accounts(MAIN_ROOT, "utama")
    show_accounts(CUSTOM_ROOT, "kustom")
    print(f"Chrome berjalan: {chrome_running()}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    {"prepare": cmd_prepare, "push": cmd_push, "status": cmd_status}.get(cmd, cmd_status)()
