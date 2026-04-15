import time
from io import BytesIO
import base64

import pyautogui
import pytesseract
from PIL import Image
from config import TESSERACT_CMD

_last_ocr_text = ""
_last_ocr_time = 0.0
_OCR_CACHE_TTL = 10
_OCR_MAX_WIDTH = 1280


def capture_screen():
    t0 = time.time()
    screenshot = pyautogui.screenshot()
    screenshot.save("screen.png")
    print(f"DEBUG -> Screenshot captured in {round(time.time() - t0, 2)}s")
    return "screen.png"


def capture_region_around_cursor(size=350):
    """Capture a small square region centered around cursor for fast vision tasks."""
    t0 = time.time()
    size = int(size or 350)
    size = max(300, min(400, size))

    x, y = pyautogui.position()
    sw, sh = pyautogui.size()
    half = size // 2

    left = max(0, min(x - half, max(0, sw - size)))
    top = max(0, min(y - half, max(0, sh - size)))

    img = pyautogui.screenshot(region=(left, top, size, size))

    # Prefer low-latency JPEG payload for Gemini vision requests.
    buffer = BytesIO()
    img = img.convert("RGB")
    img.save(buffer, format="JPEG", quality=78, optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")

    out_path = "screen_cursor_region.jpg"
    try:
        img.save(out_path, format="JPEG", quality=78, optimize=True)
    except Exception:
        out_path = None

    print(
        "DEBUG -> Cursor region captured in",
        f"{round(time.time() - t0, 2)}s",
        f"(cursor={x},{y} region={left},{top},{size},{size})",
    )
    return {
        "image_base64": encoded,
        "mime_type": "image/jpeg",
        "path": out_path,
        "cursor": {"x": int(x), "y": int(y)},
        "region": {"left": int(left), "top": int(top), "size": int(size)},
    }


def extract_text(image_path):
    global _last_ocr_text, _last_ocr_time
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    t0 = time.time()
    image = Image.open(image_path)
    w, h = image.size
    if w > _OCR_MAX_WIDTH:
        ratio = _OCR_MAX_WIDTH / w
        image = image.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
    text = pytesseract.image_to_string(image)
    elapsed = round(time.time() - t0, 2)
    _last_ocr_text = text
    _last_ocr_time = time.time()
    print(f"DEBUG -> OCR done in {elapsed}s ({w}x{h} -> {image.size[0]}x{image.size[1]})")
    return text


def get_cached_ocr(max_age=_OCR_CACHE_TTL):
    """Return cached OCR text if it's fresh enough, else None."""
    if _last_ocr_text and (time.time() - _last_ocr_time) < max_age:
        print("DEBUG -> Using cached OCR (age:", round(time.time() - _last_ocr_time, 1), "s)")
        return _last_ocr_text
    return None
