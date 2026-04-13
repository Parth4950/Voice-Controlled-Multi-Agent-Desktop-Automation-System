import time

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
