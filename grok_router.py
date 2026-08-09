# ⚠️ STATUS: FITUR BELUM SELESAI (WIP) ⚠️
# Fitur Connect X.com (Grok) ke 9Router masih dalam pengembangan & BELUM berfungsi penuh.
# Masalah yang tersisa:
#   - Cloudflare memblokir accounts.x.ai di profil kustom otomasi (block fluktuatif;
#     IP & Chrome utama bersih — ditandai hanya pada profil kustom/Playwright).
#   - Saat halaman lolos block, klik 'Login with Google' belum membuka popup OAuth
#     (JS halaman sebagian gagal dimuat — 'unexpected token <').
#   - Perlu reset profil kustom baru + cooldown sebelum diuji ulang.
import asyncio
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(__file__).parent
CONFIG_FILE = BASE / "config.json"
ACCOUNTS_FILE = BASE / "akungsuite.txt"
RESULT_FILE = BASE / "9router_keys.txt"
# Chrome 151+ menolak remote debugging pada direktori User Data bawaan.
# Otomasi selalu di salinan profil (profiles/utama), sama seperti login.py.
CUSTOM_ROOT = BASE / "profiles" / "utama"

# Ekstensi Turnstile Patcher (dari project bercocok-tanam): memanipulasi
# screenX/screenY event mouse supaya Cloudflare Turnstile menilai lebih manusiawi.
TURNSTILE_EXT = BASE.parent / "bercocok-tanam" / "turnstile"


def launch_args(profile):
    args = [
        f"--profile-directory={profile}",
        "--start-maximized",
        "--disable-blink-features=AutomationControlled",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if (TURNSTILE_EXT / "manifest.json").exists():
        args.append("--disable-extensions-except=" + str(TURNSTILE_EXT))
        args.append("--load-extension=" + str(TURNSTILE_EXT))
        print(f"  [EXT] Turnstile Patcher dimuat: {TURNSTILE_EXT}")
    return args

# Cookie sesi X/Grok tidak lagi dipakai: 9router membuat device-code sendiri dan
# kita hanya perlu menyelesaikan otorisasi di accounts.x.ai memakai sesi Google
# GSuite yang sudah ada di profile Chrome.

from login import BROWSER_NAME, BROWSER_PROC_NAME, CHROME_PATH, STEALTH_INIT_SCRIPT, set_page_zoom, type_human


def load_config():
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


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


def main_path():
    cfg = load_config()
    p = Path(cfg.get("chrome_main_path", ""))
    if p.exists():
        return p
    return Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data"


def chrome_running():
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {BROWSER_PROC_NAME}", "/NH"],
            capture_output=True, text=True, timeout=10,
        )
        return BROWSER_PROC_NAME in out.stdout
    except Exception:
        return False


def is_auth_domain(d):
    x = d.lower().lstrip(".")
    return (x == "grok.com" or x.endswith(".grok.com")
            or x == "grokipedia.com" or x.endswith(".grokipedia.com")
            or x == "x.ai" or x.endswith(".x.ai"))


def expand_sso_cookies(cookies):
    """Port dari expandSsoCookies (src/providers/router/index.js di bercocok-tanam)."""
    out, seen = [], set()

    def push(c):
        clean = {
            "name": c["name"],
            "value": c["value"],
            "domain": c["domain"],
            "path": c.get("path") or "/",
            "expires": c.get("expires", -1) if isinstance(c.get("expires"), (int, float)) and c.get("expires", 0) > 0 else -1,
            "httpOnly": bool(c.get("httpOnly")),
            "secure": c.get("secure", True),
            "sameSite": c.get("sameSite") or "Lax",
        }
        key = f"{clean['name']}|{clean['domain']}|{clean['path']}"
        if key in seen:
            return
        seen.add(key)
        out.append(clean)

    for c in cookies:
        d = c.get("domain") or ""
        if not d or not c.get("name"):
            continue
        if not AUTH_RE.match(c["name"]):
            continue
        if not is_auth_domain(d):
            continue
        push(c)

    for c in list(out):
        for dom in SSO_DOMAINS:
            push({**c, "domain": dom})
    return out


async def body_text(page):
    try:
        return (await page.evaluate("() => document.body ? document.body.innerText : ''")).lower()
    except Exception:
        return ""


BLOCK_MARKERS = ("you have been blocked", "unable to access",
                 "security service", "ray id", "turnstile", "verify you are human")


def is_blocked_text(text):
    return any(m in text for m in BLOCK_MARKERS)


async def wait_unblock(page, label, timeout_s=600):
    """Kalau Cloudflare memblokir accounts.x.ai, minta user menyelesaikan
    challenge di tab browser yang terbuka, lalu tunggu sampai lolos."""
    text = await body_text(page)
    if not is_blocked_text(text):
        return True
    print(f"\n  ⚠️  Cloudflare memblokir accounts.x.ai ({label}).")
    print("      Selesaikan verifikasi di tab browser yang terbuka (centang/klik),")
    print("      lalu tunggu — proses lanjut otomatis...")
    for i in range(timeout_s // 5):
        await page.wait_for_timeout(5000)
        text = await body_text(page)
        if not is_blocked_text(text):
            print(f"  ✅ {label}: challenge selesai, lanjut...")
            return True
        if (i + 1) % 12 == 0:
            print(f"  ...masih menunggu Anda menyelesaikan Cloudflare ({int((i + 1) * 5)}s)")
    return False


async def safe_goto(page, url, timeout_ms=90000):
    """Navigasi dengan retry — accounts.x.ai kadang timeout memuat halaman."""
    for _ in range(3):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            return True
        except Exception as e:
            print(f"  [DEBUG] goto {url[:60]} gagal ({type(e).__name__}) — coba lagi...")
            await page.wait_for_timeout(3000)
    return False


async def click_text_native(page, needles, timeout_ms):
    """Klik native (event mouse asli Playwright) pada elemen yang teksnya persis
    salah satu needle. Dibutuhkan untuk tombol yang membuka popup (user gesture),
    mis. 'Login with Google' di accounts.x.ai — el.click() via JS dianggap
    bukan gesture sehingga popup diblokir browser."""
    deadline = asyncio.get_event_loop().time() + timeout_ms / 1000
    while asyncio.get_event_loop().time() < deadline:
        for n in needles:
            loc = page.locator("button, a, [role='button'], label").filter(
                has_text=re.compile("^" + re.escape(n.strip()) + "$", re.I)).first
            try:
                if await loc.count() and await loc.is_visible():
                    await loc.click(timeout=3000)
                    return True
            except Exception:
                pass
        await asyncio.sleep(0.5)
    return False


async def click_text(page, needles, timeout_ms, exact=False):
    """Klik elemen (button/a/[role=button]/input[type=submit]/label) yang teksnya
    mengandung salah satu `needles`. exact=True memaksa kecocokan persis
    (mis. 'Continue' tidak boleh kena 'Continue with email')."""
    deadline = asyncio.get_event_loop().time() + timeout_ms / 1000
    while asyncio.get_event_loop().time() < deadline:
        ok = await page.evaluate("""(args) => {
            const { needles, exact } = args;
            const els = Array.from(document.querySelectorAll(
                'button, a, [role="button"], input[type="submit"], label'));
            const target = needles.map((n) => n.toLowerCase());
            let cands = [];
            for (const e of els) {
                const t = ((e.textContent || e.value ||
                    e.getAttribute('aria-label') || '') + '')
                    .replace(/\\s+/g, ' ').trim().toLowerCase();
                if (!t) continue;
                for (const n of target) {
                    if (exact ? t === n : (t === n || t.includes(n))) {
                        cands.push({ e: e, t: t, len: t.length });
                        break;
                    }
                }
            }
            cands.sort((a, b) => a.len - b.len);
            const best = cands[0];
            if (!best) return false;
            if (best.e.disabled) { best.e.removeAttribute('disabled'); best.e.disabled = false; }
            best.e.click();
            return true;
        }""", {"needles": list(needles), "exact": bool(exact)})
        if ok:
            return True
        await asyncio.sleep(0.5)
    return False


async def ensure_xai_login(page, email, password):
    """Login accounts.x.ai sebagai `email` memakai sesi Google GSuite profile Chrome.
    Alur (sesuai tes manual):
      1. Buka https://accounts.x.ai/account — kalau sudah login sebagai target, selesai.
      2. Kalau sesi akun lain: klik 'Sign out' (diarahkan ke /sign-in).
      3. Di /sign-in klik 'Login with Google' (bisa membuka popup) -> chooser Google
         (pilih akun target) atau form email + password.
      4. Tunggu popup menutup, reload /account, verifikasi email target."""
    await page.goto("https://accounts.x.ai/account", wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(3000)
    if not await wait_unblock(page, "halaman account"):
        return "cloudflare-block-belum-selesai"

    email_l = email.lower()
    for _ in range(2):
        text = await body_text(page)
        url = page.url
        if "accounts.x.ai/account" in url and email_l in text:
            return "ok"

        # Sesi akun lain terpasang -> sign out dulu
        if await click_text(page, ["Sign out"], 4000, exact=True):
            for _ in range(20):
                if "sign-in" in page.url:
                    break
                await page.wait_for_timeout(1000)

        # Klik 'Login with Google' (native, popup diizinkan); tangkap popup bila muncul
        gpage = page
        ok = False
        try:
            async with page.context.expect_page(timeout=20000) as pinfo:
                ok = await click_text_native(page, ["Login with Google"], 10000)
            gpage = await pinfo.value
            print(f"  [DEBUG] Google dibuka di popup: {gpage.url[:80]}")
            await set_page_zoom(gpage)
            await gpage.add_init_script(STEALTH_INIT_SCRIPT)
        except Exception:
            pass
        if not ok:
            return "tombol-login-with-google-tidak-ditemukan"

        res = await finish_google_login(gpage, email, password)
        if res != "ok":
            return res

        # Tunggu popup menutup (OAuth selesai), lalu reload halaman utama
        if gpage is not page:
            try:
                await gpage.wait_for_event("close", timeout=45000)
            except Exception:
                pass
        await safe_goto(page, "https://accounts.x.ai/account")
        await page.wait_for_timeout(2500)
        if not await wait_unblock(page, "halaman account (reload)"):
            return "cloudflare-block-belum-selesai"
        text = await body_text(page)
        if email_l in text:
            return "ok"
    return "login-xai-belum-selesai"


async def finish_google_login(page, email, password):
    """Selesaikan halaman Google: pilih akun target di chooser, atau isi form
    email + password bila akun tidak muncul (lffjp belum login di Chrome)."""
    email_l = email.lower()
    for _ in range(20):
        if "accounts.google.com" in page.url:
            break
        await page.wait_for_timeout(1000)

    picked = await page.evaluate("""(email) => {
        const el = document.querySelector('div[data-email="' + email + '"]');
        if (el) { el.click(); return true; }
        return false;
    }""", email_l)
    if not picked:
        dump = await page.evaluate("""() => ({
            url: location.href.slice(0, 120),
            emails: Array.from(document.querySelectorAll('div[data-email]'))
                .map(e => e.getAttribute('data-email')),
            hasForm: !!document.querySelector('#identifierId'),
        })""")
        print(f"  [DEBUG] chooser: url={dump['url']} emails={dump['emails'][:12]} "
              f"hasForm={dump['hasForm']}")
        if not password:
            return "akun-tidak-di-chooser-tanpa-password"
        try:
            el = page.locator("#identifierId")
            await el.wait_for(state="visible", timeout=8000)
            await type_human(page, el, email)
            await page.click("#identifierNext")
        except Exception:
            return "form-email-google-tidak-ditemukan"
        for _ in range(12):
            if "captcha" in page.url or "challenge" in page.url:
                return "captcha-menunggu-manual"
            pwd = page.locator('input[name="Passwd"], input[type="password"]').first
            if await pwd.count() and await pwd.is_visible():
                await type_human(page, pwd, password)
                await page.click("#passwordNext")
                break
            await page.wait_for_timeout(1000)

    # Tunggu keluar dari accounts.google.com (navigasi biasa ATAU popup OAuth)
    for _ in range(40):
        if "accounts.google.com" not in page.url:
            return "ok"
        await page.wait_for_timeout(1000)
    return "google-login-belum-selesai"


async def authorize_device(page, verify_url, email, password):
    """Buka verification_uri_complete (accounts.x.ai/oauth2/device?user_code=...),
    klik 'Continue' lalu 'Allow' sampai halaman 'Device Authorized'."""
    await safe_goto(page, verify_url)
    await page.wait_for_timeout(3000)
    if not await wait_unblock(page, "halaman otorisasi device"):
        return "cloudflare-block-belum-selesai"

    if not await click_text(page, ["Continue"], 4000, exact=True):
        # Sesi x.ai kedaluwarsa -> login dulu di tab ini
        res = await ensure_xai_login(page, email, password)
        if res != "ok":
            return f"login-xai-untuk-device-gagal ({res})"
        if not await click_text(page, ["Continue"], 6000, exact=True):
            return "tombol-continue-tidak-ditemukan"
    await page.wait_for_timeout(3000)

    if not await click_text(page, ["Allow"], 10000, exact=True):
        return "tombol-allow-tidak-ditemukan"

    for _ in range(20):
        url = page.url
        text = await body_text(page)
        if "device/done" in url or "device authorized" in text:
            return "ok"
        await page.wait_for_timeout(1000)
    return "device-authorize-belum-selesai"


async def click_add_button(page, timeout_ms):
    """Klik tombol 'Add' pada halaman provider 9router.
    Teks tombol berisi ikon Material ('add') + label ('Add') sehingga teks
    normalnya 'addadd' — cocokkan dengan pola tsb."""
    deadline = asyncio.get_event_loop().time() + timeout_ms / 1000
    while asyncio.get_event_loop().time() < deadline:
        ok = await page.evaluate("""() => {
            const els = Array.from(document.querySelectorAll('button, [role="button"], a'));
            const el = els.find((e) => {
                const t = ((e.textContent || '') + '').replace(/\\s+/g, '').toLowerCase();
                return t === 'add' || t === 'addadd'
                    || t === 'addconnection' || t === 'addconnectionadd';
            });
            if (!el) return false;
            el.click();
            return true;
        }""")
        if ok:
            return True
        await asyncio.sleep(0.5)
    return False


async def read_add_modal(page):
    """Baca URL otorisasi (accounts.x.ai/oauth2/device?user_code=...) dari modal Add 9router."""
    return await page.evaluate("""() => {
        const mods = Array.from(document.querySelectorAll(
            '[role="dialog"], [class*="fixed inset-0"]'));
        const el = mods[0];
        if (!el) return '';
        const txt = (el.innerText || '');
        const m = txt.match(/https:\\/\\/accounts\\.x\\.ai\\/oauth2\\/device\\?user_code=[A-Z0-9-]+/i);
        return m ? m[0] : '';
    }""")


async def wait_add_modal(page, timeout_ms=45000):
    """Tunggu modal Add memuat URL otorisasi (bisa beberapa detik setelah klik)."""
    deadline = asyncio.get_event_loop().time() + timeout_ms / 1000
    last_state = ""
    while asyncio.get_event_loop().time() < deadline:
        url = await read_add_modal(page)
        if url:
            return url
        last_state = await modal_state(page)
        await asyncio.sleep(1.5)
    print(f"  [9Router] DEBUG modal terakhir: {last_state[:300]}")
    return ""


async def modal_state(page):
    """Status modal 9router: '' bila tertutup, atau innerText lowercased."""
    return await page.evaluate("""() => {
        const mods = Array.from(document.querySelectorAll(
            '[role="dialog"], [class*="fixed inset-0"]'));
        const el = mods[0];
        return el ? (el.innerText || '').toLowerCase() : '';
    }""")


async def wait_router_account(dpage, dash_url, email, timeout_s=180):
    """Tunggu modal berubah dari 'Waiting for authorization...' lalu verifikasi
    akun muncul di daftar Connections (refresh halaman)."""
    email_l = email.lower()
    for i in range(timeout_s // 3):
        await dpage.wait_for_timeout(3000)
        state = await modal_state(dpage)
        if state and "waiting for authorization" in state:
            continue
        # Modal tertutup / berubah: sukses, error, atau sukses tanpa email di daftar
        try:
            await dpage.goto(dash_url, wait_until="domcontentloaded", timeout=30000)
        except Exception:
            pass
        await dpage.wait_for_timeout(2500)
        txt = await body_text(dpage)
        if email_l in txt:
            return True
        if state and ("success" in state or "connected" in state
                      or "authorized" in state or "added" in state):
            return True
        if state and ("error" in state or "fail" in state):
            return False
        if (i + 1) % 10 == 0:
            print(f"  [9Router] Menunggu akun muncul... {int((i + 1) * 3)}s")
    return False


async def connect_router9(context, cfg, email, password):
    """Alur 9router (sesuai tes manual):
      1. Tab pertama: buka dashboard provider grok-cli -> klik Add -> modal device code.
      2. Login accounts.x.ai sebagai target (Sign out dulu bila sesi lain).
      3. Otorisasi device: buka verification URL -> Continue -> Allow.
      4. Kembali ke dashboard: tunggu akun muncul di daftar Connections."""
    base = (cfg.get("router9_url") or "").rstrip("/")
    dash_url = base + "/dashboard/providers/grok-cli"

    # 1) Dashboard 9router + klik Add (modal dibiarkan terbuka)
    dpage = await context.new_page()
    await set_page_zoom(dpage)
    await dpage.add_init_script(STEALTH_INIT_SCRIPT)
    try:
        await dpage.goto(dash_url, wait_until="domcontentloaded", timeout=45000)
        await dpage.wait_for_timeout(3000)
        if not await click_add_button(dpage, 6000):
            return "tombol-add-tidak-ditemukan"
        verify_url = await wait_add_modal(dpage)
        print(f"  [9Router] Modal Add dibuka, user_code: "
              f"{verify_url.split('user_code=')[-1] if verify_url else '(tidak terbaca)'}")
        if not verify_url:
            return "modal-add-tanpa-url-otorisasi"

        # 2) Login accounts.x.ai
        apage = await context.new_page()
        try:
            await set_page_zoom(apage)
            await apage.add_init_script(STEALTH_INIT_SCRIPT)
            res = await ensure_xai_login(apage, email, password)
            if res != "ok":
                return res
            print("  [9Router] Login accounts.x.ai OK.")
        finally:
            await apage.close()

        # 3) Otorisasi device
        vpage = await context.new_page()
        try:
            await set_page_zoom(vpage)
            await vpage.add_init_script(STEALTH_INIT_SCRIPT)
            res = await authorize_device(vpage, verify_url, email, password)
            if res != "ok":
                return f"authorize-gagal ({res})"
        finally:
            await vpage.close()

        # 4) Verifikasi akun muncul di dashboard
        ok = await wait_router_account(dpage, dash_url, email)
        return "✅ sukses" if ok else "authorize-selesai-tapi-akun-belum-muncul"
    finally:
        try:
            await dpage.close()
        except Exception:
            pass


def log_result(email, status):
    RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with RESULT_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{email}|{status}|{stamp}\n")


async def process_account(context, email, password, cfg):
    print(f"  Proses akun: {email}...")
    return await connect_router9(context, cfg, email, password)


async def main():
    accounts = load_accounts()

    limit = None
    email_only = None
    profile = "Default"
    for i, arg in enumerate(sys.argv):
        if arg == "--limit" and i + 1 < len(sys.argv):
            try:
                limit = int(sys.argv[i + 1])
            except ValueError:
                pass
        elif arg == "--email" and i + 1 < len(sys.argv):
            email_only = sys.argv[i + 1].strip().lower()
        elif arg == "--profile" and i + 1 < len(sys.argv):
            profile = sys.argv[i + 1].strip()
    if email_only:
        match = [a for a in accounts if a[0].lower() == email_only]
        if match:
            accounts = match
        else:
            # Akun tanpa password = pakai sesi Google yang sudah ada di Chrome.
            print(f"  (--email) {email_only} tidak ada di akungsuite.txt — pakai sesi yang ada.")
            accounts = [(email_only, None)]
    if limit is not None:
        accounts = accounts[:limit]

    cfg = load_config()
    if not cfg.get("router9_url"):
        print("❌ 9Router belum dikonfigurasi. Isi router9_url di config.json.")
        return
    if not accounts:
        print("akungsuite.txt kosong.")
        return
    if chrome_running():
        print(f"⚠️ {BROWSER_NAME} sedang berjalan — tutup SEMUA window dulu,")
        print("   lalu jalankan ulang. (Profil terkunci saat browser terbuka)")
        return

    # Profil kustom = snapshot profil utama (sesi GSuite ikut tersalin).
    # Dibuat/diperbarui otomatis lewat sync.py prepare dengan profile terpilih.
    print(f"[PREPARE] Menyiapkan snapshot profil utama ('{profile}') untuk otomasi...")
    r = subprocess.run([sys.executable, "-u", "sync.py", "prepare", "--profile", profile],
                       cwd=BASE)
    if r.returncode != 0 or not (CUSTOM_ROOT / profile).exists():
        print("❌ Prepare gagal — cek lokasi browser utama di config.json.")
        return
    print("[PREPARE] Selesai.")

    print(f"=== CONNECT X.COM (GROK) KE 9ROUTER — {len(accounts)} akun GSuite ===")
    print(f"Profil kustom '{profile}' (snapshot utama) dibuka; sesi Google dipakai untuk login X.")
    print("Jika halaman captcha/verifikasi muncul: selesaikan manual, hasil dicatat per akun.\n")

    playwright = await async_playwright().start()
    try:
        print(f"[START] Membuka browser otomasi (profil kustom '{profile}')...", flush=True)
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(CUSTOM_ROOT),
            executable_path=CHROME_PATH,
            headless=False,
            timeout=30000,
            viewport=None,
            args=launch_args(profile),
        )
        print(f"[START] Browser terbuka, tab awal: {len(context.pages)}", flush=True)
    except Exception as e:
        print(f"Gagal buka profil kustom: {e}")
        return

    results = {}
    try:
        for i, (email, password) in enumerate(accounts):
            label = email.split("@")[0]
            print(f"\n=== [{i + 1}/{len(accounts)}] {label} ===", flush=True)
            try:
                status = await process_account(context, email, password, cfg)
            except Exception as e:
                status = f"error: {type(e).__name__}: {e}"
            results[label] = status
            log_result(email, status)
            print(f"  HASIL: {status}")
            await asyncio.sleep(2)

        print("\n=== RINGKASAN ===")
        sukses = 0
        for label, status in results.items():
            print(f"  {label}: {status}")
            if status == "✅ sukses":
                sukses += 1
        print(f"\nSukses: {sukses}/{len(results)} — rincian lengkap di 9router_keys.txt")

        if any("manual" in s for s in results.values()):
            print("\nAda akun yang butuh tindakan manual (captcha/verifikasi).")
            print("Selesaikan di tab yang terbuka, lalu tutup window browser.")
            while len(context.pages) > 0:
                await asyncio.sleep(5)
        else:
            await context.close()
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        try:
            await playwright.stop()
        except Exception:
            pass


if __name__ == "__main__":
    if "--list" in sys.argv:
        from sync import cmd_list
        cmd_list()
    else:
        asyncio.run(main())
