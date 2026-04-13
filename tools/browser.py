"""Browser automation layer — Playwright primary, direct-URL fallback.

Public API used by system_tools and automation flows:
    get_browser()       → returns a live Playwright Browser or None
    new_page(url)       → open url in a managed page, return Page or None
    safe_click(page, selector, **kw)  → layered click, returns bool
    wait_ready(page)    → wait until network is idle
    extract_text(page)  → return visible text content
    close_browser()     → tear down the browser cleanly
    is_browser_alive()  → health check
"""

from tools.log import safe_log
from config import PLAYWRIGHT_USER_DATA_DIR

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout
    _PW_OK = True
except ImportError:
    _PW_OK = False

_pw = None
_browser = None

_LAUNCH_ARGS = [
    "--start-maximized",
    "--disable-blink-features=AutomationControlled",
]
_USER_DATA_DIR = PLAYWRIGHT_USER_DATA_DIR


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

def _ensure_pw():
    global _pw
    if _pw is None and _PW_OK:
        try:
            _pw = sync_playwright().start()
        except Exception as e:
            safe_log("DEBUG -> Playwright runtime failed to start:", e)
            _pw = None
    return _pw


def is_browser_alive():
    """Works for both Browser and BrowserContext (from launch_persistent_context)."""
    if _browser is None:
        return False
    try:
        _ = _browser.pages
        return True
    except Exception:
        return False


def close_browser():
    global _browser
    if _browser is None:
        return
    try:
        _browser.close()
    except Exception:
        pass
    _browser = None


def get_browser(force_restart=False):
    global _browser

    if not _PW_OK:
        return None

    if force_restart:
        close_browser()

    if is_browser_alive():
        return _browser

    close_browser()
    pw = _ensure_pw()
    if pw is None:
        return None

    try:
        _browser = pw.chromium.launch_persistent_context(
            user_data_dir=_USER_DATA_DIR,
            headless=False,
            args=_LAUNCH_ARGS,
            no_viewport=True,
        )
        return _browser
    except Exception as e:
        safe_log("DEBUG -> Playwright browser launch failed:", e)
        _browser = None
        return None


# ---------------------------------------------------------------------------
# Page helpers
# ---------------------------------------------------------------------------

def new_page(url=None):
    ctx = get_browser()
    if ctx is None:
        return None
    try:
        page = ctx.new_page()
        if url:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
        return page
    except Exception as e:
        safe_log("DEBUG -> new_page failed:", e)
        return None


def wait_ready(page, timeout_ms=8000):
    if page is None:
        return
    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except Exception:
        pass


def extract_text(page):
    if page is None:
        return ""
    try:
        return page.inner_text("body") or ""
    except Exception:
        return ""


def safe_click(page, selector, timeout_ms=6000):
    """Layered click: normal → force → JS dispatch.  Returns bool."""
    if page is None:
        return False

    try:
        loc = page.locator(selector).first
        loc.wait_for(state="visible", timeout=timeout_ms)
    except Exception:
        return False

    try:
        loc.click(timeout=3000)
        return True
    except Exception:
        pass

    try:
        loc.click(force=True, timeout=3000)
        return True
    except Exception:
        pass

    try:
        loc.evaluate("el => el.click()")
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# General web automation helpers
# ---------------------------------------------------------------------------

_active_page = None


def get_active_page():
    """Return the most recently used page, or None."""
    global _active_page
    if _active_page is not None:
        try:
            _ = _active_page.url
            return _active_page
        except Exception:
            _active_page = None

    ctx = get_browser()
    if ctx is None:
        return None
    pages = ctx.pages
    if pages:
        _active_page = pages[-1]
        return _active_page
    return None


def navigate_to(url):
    """Navigate to a URL, reusing the active page or opening a new one.
    Returns the page on success, None on failure."""
    global _active_page
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    page = get_active_page()
    if page is None:
        page = new_page(url)
        _active_page = page
        return page
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        _active_page = page
        return page
    except Exception as e:
        safe_log("DEBUG -> navigate_to failed:", e)
        return None


def type_text(selector, text):
    """Type text into a form field on the active page. Returns bool."""
    page = get_active_page()
    if page is None:
        return False
    try:
        loc = page.locator(selector).first
        loc.wait_for(state="visible", timeout=5000)
        loc.fill(text, timeout=5000)
        return True
    except Exception as e:
        safe_log("DEBUG -> type_text failed:", e)
        return False


def scroll_page(direction="down"):
    """Scroll the active page up or down. Returns bool."""
    page = get_active_page()
    if page is None:
        return False
    try:
        delta = 600 if direction == "down" else -600
        page.mouse.wheel(0, delta)
        return True
    except Exception as e:
        safe_log("DEBUG -> scroll_page failed:", e)
        return False


def click_element(target):
    """Click an element by CSS selector or visible text. Returns bool."""
    page = get_active_page()
    if page is None:
        return False

    # Try as CSS selector first
    if safe_click(page, target, timeout_ms=3000):
        return True

    # Fall back to text-based click
    try:
        loc = page.get_by_text(target, exact=False).first
        loc.click(timeout=4000)
        return True
    except Exception:
        pass

    try:
        loc = page.get_by_role("link", name=target).first
        loc.click(timeout=3000)
        return True
    except Exception:
        pass

    safe_log(f"DEBUG -> click_element failed for target: {target}")
    return False


def get_page_text():
    """Extract visible text from the active page."""
    page = get_active_page()
    return extract_text(page)
