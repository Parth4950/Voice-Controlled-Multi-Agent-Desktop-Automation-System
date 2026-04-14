"""Centralised machine-specific paths and app mappings.

Reads overrides from ``config.json`` next to this file when it exists,
so users can customise without editing Python source.
"""

import json
import os
from pathlib import Path

_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
_overrides = {}
if os.path.exists(_CONFIG_FILE):
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as _f:
            _overrides = json.load(_f)
    except Exception:
        pass


def _get(key, default):
    return _overrides.get(key, default)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def get_bruh_files_root() -> Path:
    """Voice-created files and folders live here (override in config.json: bruh_files_root)."""
    custom = _get("bruh_files_root", None)
    if custom:
        return Path(os.path.expandvars(str(custom))).expanduser().resolve()
    return (Path.home() / "Documents" / "BruhFiles").resolve()


def get_filesystem_scope() -> str:
    """Where file commands may touch: ``home`` (under user profile + Bruh root) or ``full`` (entire PC)."""
    v = (str(_get("filesystem_scope", "full")) or "full").strip().lower()
    return v if v in ("home", "full") else "full"


TESSERACT_CMD = _get(
    "tesseract_cmd",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
)

PLAYWRIGHT_USER_DATA_DIR = _get(
    "playwright_user_data_dir",
    r"C:\Users\chand\AppData\Local\Google\Chrome\BruhProfile-PW",
)

# ---------------------------------------------------------------------------
# App map & fallbacks  (keys are lowercase friendly names)
# ---------------------------------------------------------------------------

APP_MAP = _get("app_map", {
    "chrome": r"C:\Users\chand\AppData\Local\Google\Chrome\Application\chrome.exe",
    "google chrome": r"C:\Users\chand\AppData\Local\Google\Chrome\Application\chrome.exe",
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "file explorer": "explorer",
    "explorer": "explorer",
    "vscode": "code",
    "visual studio code": "code",
    "spotify": r"C:\Users\chand\AppData\Local\Microsoft\WindowsApps\Spotify.exe",
    "youtube": "https://www.youtube.com",
    "netflix": "https://www.netflix.com",
})

APP_FALLBACKS = _get("app_fallbacks", {
    "spotify": [
        r"C:\Users\chand\AppData\Roaming\Spotify\Spotify.exe",
        r"C:\Users\chand\AppData\Local\Microsoft\WindowsApps\Spotify.exe",
        "spotify:",
    ],
    "vscode": [
        r"C:\Users\chand\AppData\Local\Programs\Microsoft VS Code\Code.exe",
        r"C:\Program Files\Microsoft VS Code\Code.exe",
        "code",
    ],
    "cursor": [
        r"C:\Users\chand\AppData\Local\Programs\Cursor\Cursor.exe",
        r"C:\Program Files\Cursor\Cursor.exe",
    ],
    "whatsapp": [
        r"C:\Users\chand\AppData\Local\WhatsApp\WhatsApp.exe",
        r"C:\Users\chand\AppData\Local\Microsoft\WindowsApps\WhatsApp.exe",
        "whatsapp:",
    ],
    "file explorer": [r"C:\Windows\explorer.exe"],
    "explorer": [r"C:\Windows\explorer.exe"],
    "haveloc": [r"C:\Program Files\Haveloc\Haveloc.exe"],
})

PROCESS_MAP = _get("process_map", {
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "notepad": "notepad.exe",
    "calculator": "Calculator.exe",
    "calc": "Calculator.exe",
    "spotify": "Spotify.exe",
    "vscode": "Code.exe",
    "visual studio code": "Code.exe",
    "cursor": "Cursor.exe",
    "whatsapp": "WhatsApp.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
})
