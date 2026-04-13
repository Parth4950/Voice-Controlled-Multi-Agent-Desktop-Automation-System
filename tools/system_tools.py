import ctypes
import os
import subprocess
import webbrowser
from datetime import datetime
from urllib.parse import quote_plus

import pyautogui

from tools.log import safe_log
from tools.browser import (
    get_browser,
    new_page,
    safe_click,
    wait_ready,
    is_browser_alive,
    close_browser,
    _PW_OK,
)
from config import APP_MAP, APP_FALLBACKS, PROCESS_MAP


def open_app(app_name):
    try:
        app_name = app_name.lower().strip()
        mapped = APP_MAP.get(app_name)
        fallbacks = APP_FALLBACKS.get(app_name, [])

        launch_targets = []
        if mapped:
            launch_targets.append(mapped)
        launch_targets.extend(fallbacks)

        for target in launch_targets:
            safe_log("DEBUG -> Launching:", target)
            if target.startswith("http"):
                webbrowser.open(target)
                return True

            is_full_path = os.path.isabs(target) or ("\\" in target) or ("/" in target)
            if is_full_path:
                if os.path.exists(target):
                    os.startfile(target)
                    return True
                continue

            try:
                subprocess.Popen(target, shell=True)
                return True
            except Exception:
                continue

        # Last resort: try os.startfile with the bare name — handles
        # Windows Store apps, URI protocols (e.g. "spotify:"), and
        # apps registered in PATH that the explicit list missed.
        try:
            safe_log("DEBUG -> Last-resort startfile:", app_name)
            os.startfile(app_name)
            return True
        except Exception:
            pass

        safe_log(f"Could not open app: {app_name}")
        return False
    except Exception:
        safe_log(f"Could not open app: {app_name}")
        return False


def close_app(app_name):
    """Kill a running application by process name using taskkill."""
    app_name = (app_name or "").strip().lower()
    if not app_name:
        return False

    process = PROCESS_MAP.get(app_name, f"{app_name}.exe")

    try:
        result = subprocess.run(
            ["taskkill", "/IM", process, "/F"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            safe_log(f"DEBUG -> Closed {process}")
            return True
        safe_log(f"DEBUG -> taskkill failed for {process}:", result.stderr.strip())
        return False
    except Exception as e:
        safe_log(f"DEBUG -> close_app error:", e)
        return False


def set_volume(action):
    """Control system volume: up, down, or mute using Windows key simulation."""
    try:
        VK_VOLUME_UP = 0xAF
        VK_VOLUME_DOWN = 0xAE
        VK_VOLUME_MUTE = 0xAD
        KEYEVENTF_KEYUP = 0x0002

        key_map = {
            "up": VK_VOLUME_UP,
            "down": VK_VOLUME_DOWN,
            "mute": VK_VOLUME_MUTE,
        }
        vk = key_map.get(action)
        if vk is None:
            return f"Unknown volume action: {action}"

        # Press 3 times for up/down to make the change noticeable
        presses = 3 if action in ("up", "down") else 1
        for _ in range(presses):
            ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)

        safe_log(f"DEBUG -> Volume {action}")
        return f"Volume {action}"
    except Exception as e:
        safe_log("DEBUG -> set_volume error:", e)
        return f"Volume control failed: {e}"


def take_screenshot():
    """Capture and save a screenshot, return the file path."""
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), f"screenshot_{ts}.png")
        shot = pyautogui.screenshot()
        shot.save(path)
        safe_log(f"DEBUG -> Screenshot saved: {path}")
        return path
    except Exception as e:
        safe_log("DEBUG -> take_screenshot error:", e)
        return None


def search_google(query):
    webbrowser.open(f"https://www.google.com/search?q={query}")


def open_website(url):
    webbrowser.open(url)


def play_youtube(query):
    webbrowser.open(f"https://www.youtube.com/results?search_query={query}")


# ---------------------------------------------------------------------------
# Playwright-based YouTube automation
# ---------------------------------------------------------------------------

def _try_click_video(page):
    """Try clicking one of the first few real video results on a YT results page."""
    # YouTube's web-component selectors (a#video-title) are invisible to
    # Playwright's DOM queries.  Standard href selectors work reliably.
    loc = page.locator('a[href^="/watch"]')
    try:
        loc.first.wait_for(state="attached", timeout=6000)
        count = loc.count()
    except Exception:
        return False

    for i in range(min(count, 8)):
        try:
            item = loc.nth(i)
            href = item.get_attribute("href", timeout=2000) or ""
            # Skip Google‑Ads bounce links that also contain /watch
            if "googleadservices" in href or "googlesyndication" in href:
                continue
            if not href.startswith("/watch"):
                continue
            item.scroll_into_view_if_needed(timeout=2000)
            item.click(timeout=4000)
            return True
        except Exception:
            continue
    return False


def play_youtube_automated(query):
    """Playwright-powered YouTube automation.

    Returns:
    - "success" when automation opens a video
    - "failed" when automation cannot complete

    The caller (execution layer) owns fallback to play_youtube().
    """
    query = query.strip()
    if query.lower().startswith("play "):
        query = query[5:].strip()

    safe_log(f"Automating on YouTube: {query}")

    if not query:
        safe_log("DEBUG -> automation skipped: empty query")
        return "failed"

    if not _PW_OK:
        safe_log("DEBUG -> Playwright not available, skipping automation")
        return "failed"

    restarted = False
    for attempt in range(2):
        if attempt == 1 and not restarted:
            break
        force = attempt == 1

        browser = get_browser(force_restart=force)
        if browser is None:
            safe_log("DEBUG -> browser not available")
            if not restarted:
                restarted = True
                continue
            return "failed"

        if not is_browser_alive():
            safe_log("DEBUG -> browser session is dead, restarting")
            restarted = True
            continue

        page = None
        try:
            page = new_page("https://www.youtube.com")
            if page is None:
                raise RuntimeError("could not open YouTube page")

            wait_ready(page, timeout_ms=8000)

            search_box = page.locator('input[name="search_query"]')
            search_box.fill(query, timeout=5000)
            search_box.press("Enter")

            page.wait_for_load_state("domcontentloaded", timeout=10000)
            wait_ready(page, timeout_ms=8000)

            if _try_click_video(page):
                safe_log("DEBUG -> Opened video with Playwright")
                return "success"

            safe_log("DEBUG -> Playwright could not click any result")
            return "failed"

        except Exception as e:
            safe_log("DEBUG -> Playwright automation error:", e)
            if page:
                try:
                    page.close()
                except Exception:
                    pass
            if not restarted:
                restarted = True
                continue
            return "failed"

    return "failed"
