import re
import time
import concurrent.futures

from context.screen import capture_screen, extract_text
from ai.gemini import ask_gemini
from memory.context import update_context, get_context
from agents.personality import bruh_prompt
from tools.log import safe_log

_CODE_GEMINI_TIMEOUT = 8
_OCR_MAX_CHARS = 1000


def _trim_ocr(text):
    if not text:
        return ""
    text = re.sub(r'[^\x20-\x7E\n]', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {3,}', ' ', text)
    return text[:_OCR_MAX_CHARS]


def run_code_agent(command):
    try:
        ctx = get_context()
        reference_words = ("it", "this", "that")

        if any(word in command for word in reference_words) and ctx.get("last_screen_text"):
            text = ctx["last_screen_text"]
        else:
            safe_log("DEBUG -> code_agent: capturing screen")
            image_path = capture_screen()
            text = extract_text(image_path)

        text = _trim_ocr(text)
        if not text or len(text.strip()) < 20:
            update_context(command=command, response="Can't see much on screen.")
            return "Can't see much on your screen right now."

        update_context(screen_text=text, command=command)
        safe_log("DEBUG -> code_agent: OCR length:", len(text))

        prompt = bruh_prompt(
            role_context=f"You are an expert software engineer.\n\nScreen content:\n{text}",
            user_context=ctx,
            user_query=command,
        )

        safe_log("DEBUG -> code_agent: calling Gemini")
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(ask_gemini, prompt)
            try:
                response = future.result(timeout=_CODE_GEMINI_TIMEOUT)
            except concurrent.futures.TimeoutError:
                safe_log("DEBUG -> code_agent: Gemini timed out")
                update_context(response="Timed out reading screen.")
                return "I see your screen but took too long to process. Try again."

        if not response:
            response = "Couldn't make sense of what's on screen."
        update_context(response=response)
        return response

    except Exception as e:
        safe_log("ERROR -> code_agent failed:", e)
        return "Screen analysis broke. Try again."
