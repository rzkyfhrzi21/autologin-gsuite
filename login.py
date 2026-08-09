import asyncio
import subprocess
import sys
import time
from pathlib import Path

from playwright.async_api import async_playwright

# Cegah crash UnicodeEncodeError di CMD Windows (emoji tidak dikenali cp1252)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
# Chrome 151 menolak remote debugging pada direktori User Data bawaan.
# Profil Default telah disalin sekali ke profiles/utama (kustom), otomasi jalan di situ.
CHROME_USER_DATA = Path(__file__).parent / "profiles" / "utama"
ACCOUNTS_FILE = Path(__file__).parent / "akungsuite.txt"

# Selector berdasarkan referensi halaman Google asli:
#   Sign in - Google Accounts.html  : #identifierId -> #identifierNext
#   Welcome.html                    : input[name="Passwd"] -> #passwordNext
#   Welcome _ captcha.html          : input[name="Passwd"] (type=text!) + #ca (captcha)
EMAIL_INPUT = "#identifierId"
EMAIL_NEXT = "#identifierNext"
PASS_INPUT = 'input[name="Passwd"]'
PASS_NEXT = "#passwordNext"
CAPTCHA_INPUT = "#ca"
CAPTCHA_IMG = "#captchaimg"

TYPE_DELAY_MS = 90

STEALTH_INIT_SCRIPT = """
(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    window.chrome = window.chrome || { runtime: {} };
    Object.defineProperty(navigator, 'languages', { get: () => ['id-ID', 'id', 'en-US', 'en'] });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    const origQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : origQuery(parameters)
    );
})();
"""


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


def chrome_running():
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq chrome.exe", "/NH"],
            capture_output=True, text=True, timeout=10,
        )
        return "chrome.exe" in out.stdout
    except Exception:
        return False


async def type_human(page, locator, value):
    await locator.click()
    await page.wait_for_timeout(400)
    for ch in value:
        await locator.type(ch)
        await page.wait_for_timeout(TYPE_DELAY_MS)
    await page.wait_for_timeout(500)


async def is_captcha_page(page):
    """Halaman ber-captcha AKTIF: elemen captcha benar-benar VISIBLE.
    Catatan: #captchaimg dan #ca selalu ada di DOM Google walau tersembunyi,
    jadi keberadaan di DOM TIDAK cukup — harus cek is_visible()."""
    try:
        img = page.locator(CAPTCHA_IMG)
        if await img.count() > 0 and await img.is_visible():
            return True
        ca = page.locator(CAPTCHA_INPUT)
        if await ca.count() > 0 and await ca.is_visible():
            return True
        return False
    except Exception:
        return False


async def has_password_field(page):
    try:
        return await page.locator(PASS_INPUT).count() > 0
    except Exception:
        return False


async def login_in_tab(context, email, password, label, results, page=None):
    # Reuse the initial blank tab so it does not remain unused.
    page = page or await context.new_page()
    await page.add_init_script(STEALTH_INIT_SCRIPT)

    try:
        print(f"[{label}] Buka halaman tambah akun (tab baru)...", flush=True)
        # AddSession = halaman login akun baru walau sudah ada sesi lain
        response = await page.goto("https://accounts.google.com/AddSession",
                                   wait_until="domcontentloaded", timeout=60000)
        print(
            f"[{label}] Halaman terbuka: {page.url} "
            f"(HTTP {response.status if response else 'n/a'})",
            flush=True,
        )
        await page.wait_for_timeout(2500)

        # ---- LANGKAH 1: EMAIL ----
        el = page.locator(EMAIL_INPUT)
        await el.wait_for(state="visible", timeout=20000)
        await type_human(page, el, email)
        await page.click(EMAIL_NEXT)
        print(f"[{label}] Email diisi, klik Next.")

        # ---- LANGKAH 2: PASSWORD (bisa muncul 1x atau 2x bila ada captcha) ----
        password_done = False
        for round_no in range(1, 4):
            await page.wait_for_timeout(3000)
            url = page.url

            # Sudah masuk? (halaman welcome/consent atau myaccount = STOP, biar user klik setuju)
            if ("myaccount.google.com" in url
                    or "accounts.google.com/signin/v2/success" in url
                    or "accounts.google.com/CheckCookie" in url):
                print(f"[{label}] Akun masuk. Berhenti — lanjut manual (setuju/captcha).")
                results[label] = "masuk-menunggu-setuju"
                return page

            # Halaman password (Welcome / Welcome captcha)
            if await has_password_field(page):
                pwd = page.locator(PASS_INPUT).first
                await pwd.wait_for(state="visible", timeout=15000)
                await type_human(page, pwd, password)
                print(f"[{label}] Password diisi (putaran {round_no}).")

                if await is_captcha_page(page):
                    # Halaman WELCOME_CAPTCHA: isi password KEDUA, lalu BERHENTI.
                    # JANGAN klik Next — captcha #ca belum diisi.
                    # User isi captcha manual, lalu klik Next/setuju sendiri.
                    print(f"[{label}] Halaman ber-CAPTCHA terdeteksi.")
                    print(f"[{label}]    Password kedua sudah terisi otomatis.")
                    print(f"[{label}]    LANJUT MANUAL di tab ini:")
                    print(f"[{label}]    isi captcha -> klik Next -> setuju.")
                    results[label] = "captcha-menunggu-manual"
                    return page

                await page.click(PASS_NEXT)
                password_done = True
                print(f"[{label}] Klik Next (password).")
                continue

            # Halaman lain tanpa password — berhenti aman (kemungkinan consent/captcha)
            print(f"[{label}] Tidak ada field password. URL: {url}")
            results[label] = "stop-unknown"
            return page

        results[label] = "selesai-otomatis"
        return page

    except Exception as e:
        print(f"[{label}] ERROR: {type(e).__name__}: {e}", flush=True)
        results[label] = f"error: {e}"
        return page


async def main():
    accounts = load_accounts()

    # Argumen CLI: --limit N (mode tes, proses N akun pertama)
    limit = None
    for i, arg in enumerate(sys.argv):
        if arg == "--limit" and i + 1 < len(sys.argv):
            try:
                limit = int(sys.argv[i + 1])
            except ValueError:
                pass
    if limit is not None:
        accounts = accounts[:limit]

    if not accounts:
        print("akungsuite.txt kosong.")
        return

    if not CHROME_USER_DATA.exists():
        print("⚠️ Profil kustom belum ada. Jalankan setup dulu (lihat README).")
        return

    if chrome_running():
        print("⚠️ Chrome sedang berjalan — tutup SEMUA window Chrome dulu,")
        print("   lalu jalankan ulang. (Profil terkunci saat Chrome terbuka)")
        return

    print(f"=== TAMBAH {len(accounts)} AKUN KE PROFIL DEFAULT (1 tab per akun) ===")
    print("Script otomatis: buka halaman tambah akun -> email -> password.")
    print("Jika halaman ber-captcha muncul: password diisi otomatis, lalu BERHENTI.")
    print("Captcha + tombol setuju: MANUAL di tiap tab.\n")

    print("[START] Memulai Playwright...", flush=True)
    playwright = await async_playwright().start()
    try:
        print("[START] Membuka Chrome dengan profil Default...", flush=True)
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=CHROME_USER_DATA,
            executable_path=CHROME_PATH,
            headless=False,
            timeout=30000,
            viewport={"width": 1366, "height": 860},
            args=[
                "--profile-directory=Default",
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )
        print(f"[START] Chrome terbuka, tab awal: {len(context.pages)}", flush=True)
    except Exception as e:
        print(f"Gagal buka profil Default: {e}")
        return

    results = {}
    pages = []
    try:
        for i, (email, password) in enumerate(accounts):
            label = email.split("@")[0]
            initial_page = None
            if i == 0 and context.pages:
                candidate = context.pages[0]
                if candidate.url in ("about:blank", "chrome://newtab/"):
                    initial_page = candidate
            pages.append(await login_in_tab(context, email, password, label, results, initial_page))

        print("\n=== RINGKASAN ===")
        for label, status in results.items():
            print(f"  {label}: {status}")
        print("\nSemua tab sengaja dibiarkan terbuka. Isi captcha & klik setuju manual per tab.")

        # Tunggu sampai user menutup browser (sesi tetap tersimpan di profil Default)
        print("\nMenunggu... tutup window Chrome bila sudah selesai.")
        while len(context.pages) > 0:
            await asyncio.sleep(5)
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        pass


if __name__ == "__main__":
    asyncio.run(main())
