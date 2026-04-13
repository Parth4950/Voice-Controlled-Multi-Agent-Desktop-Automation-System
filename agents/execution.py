import re
import time
import concurrent.futures

from tools.system_tools import (
    close_app,
    open_app,
    open_website,
    play_youtube,
    play_youtube_automated as play_youtube_advanced,
    search_google,
    set_volume,
    take_screenshot,
)
from tools.browser import (
    navigate_to,
    type_text,
    scroll_page,
    click_element,
    get_page_text,
)
from tools.log import safe_log, now_ms, log_timing
from memory.memory import remember, recall
from context.screen import capture_screen, extract_text, get_cached_ocr
from ai.gemini import ask_gemini
from agents.personality import bruh_prompt

_SCREEN_GEMINI_TIMEOUT = 8
_OCR_MAX_CHARS = 1000


def _trim_ocr(text):
    if not text:
        return ""
    text = re.sub(r'[^\x20-\x7E\n]', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {3,}', ' ', text)
    return text[:_OCR_MAX_CHARS]


def _is_useless_ocr(text):
    if not text or len(text.strip()) < 20:
        return True
    alnum = sum(1 for c in text if c.isalnum())
    total = len(text)
    if total > 0 and alnum / total < 0.3:
        return True
    words = text.split()
    if len(words) < 5:
        return True
    return False


def _ask_gemini_with_timeout(prompt, timeout=_SCREEN_GEMINI_TIMEOUT):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(ask_gemini, prompt)
        return future.result(timeout=timeout)


def execute(intent, params):
    if intent == "analyze_context":
        safe_log("DEBUG -> Screen pipeline start")
        try:
            query = params.get("query", "")
            _followup_hints = ("explain", "more", "what about", "tell me more", "elaborate", "go on", "details")
            cached = None
            if any(h in query.lower() for h in _followup_hints):
                cached = get_cached_ocr()

            if cached:
                raw_text = cached
            else:
                ocr_start = now_ms()
                img = capture_screen()
                raw_text = extract_text(img)
                log_timing("screen_ocr", ocr_start)
            text = _trim_ocr(raw_text)

            if _is_useless_ocr(text):
                safe_log("DEBUG -> OCR useless, skipping Gemini")
                return "Can't see much on your screen right now."

            safe_log("DEBUG -> OCR length:", len(text))

            prompt = bruh_prompt(
                role_context=f"The user is looking at this screen:\n\n{text}",
                user_context="",
                user_query=params["query"],
            )

            safe_log("DEBUG -> Gemini start for screen")
            gemini_start = now_ms()
            try:
                response = _ask_gemini_with_timeout(prompt)
            except concurrent.futures.TimeoutError:
                safe_log("DEBUG -> Gemini timed out for screen analysis")
                return "I see your screen but took too long to process. Try again."
            log_timing("screen_gemini", gemini_start)

            if not response:
                return "Couldn't make sense of what's on screen."
            return response

        except Exception as e:
            safe_log("ERROR -> Screen analysis failed:", e)
            return "Screen analysis broke. Try again."
    elif intent == "remember":
        remember(params["key"], params["value"])
    elif intent == "recall":
        value = recall(params["key"])
        return value
    elif intent == "open_app":
        print("DEBUG -> App to open:", params["app"])
        return open_app(params["app"])
    elif intent == "close_app":
        print("DEBUG -> App to close:", params["app"])
        return close_app(params["app"])
    elif intent == "volume":
        return set_volume(params["action"])
    elif intent == "screenshot":
        path = take_screenshot()
        return f"Screenshot saved to {path}" if path else "Screenshot failed"
    elif intent == "search":
        search_google(params["query"])
    elif intent == "open_website":
        open_website(params["url"])
    elif intent == "play_media":
        print("DEBUG -> Media query:", params["query"])
        play_youtube(params["query"])
    elif intent == "navigate":
        url = params.get("url", "")
        safe_log("DEBUG -> Navigating to:", url)
        page = navigate_to(url)
        return "Navigated" if page else "Couldn't open that page"
    elif intent == "web_click":
        target = params.get("target", "")
        safe_log("DEBUG -> Clicking:", target)
        ok = click_element(target)
        return "Clicked" if ok else f"Couldn't find '{target}' to click"
    elif intent == "web_type":
        text = params.get("text", "")
        selector = params.get("selector", "input:visible, textarea:visible")
        safe_log("DEBUG -> Typing:", text)
        ok = type_text(selector, text)
        return "Typed" if ok else "Couldn't find a field to type in"
    elif intent == "web_scroll":
        direction = params.get("direction", "down")
        safe_log("DEBUG -> Scrolling:", direction)
        ok = scroll_page(direction)
        return f"Scrolled {direction}" if ok else "Couldn't scroll"
    elif intent == "play_media_advanced":
        print("DEBUG -> Automation query:", params["query"])
        status = "failed"
        try:
            result = play_youtube_advanced(params["query"])
            status = result if result in {"success", "failed"} else "failed"
        except Exception as e:
            safe_log("DEBUG -> play_media_advanced failed:", e)
            status = "failed"
        if status != "success":
            safe_log("DEBUG -> Falling back to fast YouTube open")
            play_youtube(params["query"])
            return "fallback"
        return "success"
