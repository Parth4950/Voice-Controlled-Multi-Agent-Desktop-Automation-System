import json
import os
import threading
import queue

import pyttsx3
from tools.log import safe_log
from ui.event_bus import emit_event
from ui.state import is_muted

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "voice_config.json")

_VOICE_ID = None
_VOICE_ID_RESOLVED = False

_speech_queue = queue.Queue()
_SENTINEL = object()


def _resolve_voice_id():
    global _VOICE_ID, _VOICE_ID_RESOLVED
    if _VOICE_ID_RESOLVED:
        return _VOICE_ID
    _VOICE_ID_RESOLVED = True

    config_id = None
    if os.path.exists(_CONFIG_PATH):
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                config_id = data.get("voice_id")
        except Exception:
            pass

    try:
        tmp = pyttsx3.init()
        voices = tmp.getProperty("voices")

        if config_id:
            for v in voices:
                if v.id == config_id:
                    _VOICE_ID = config_id
                    break

        if not _VOICE_ID:
            for v in voices:
                if "zira" in (v.name or "").lower():
                    _VOICE_ID = v.id
                    break

        if not _VOICE_ID and voices:
            _VOICE_ID = voices[0].id

        del tmp
    except Exception as e:
        safe_log("DEBUG -> TTS voice probe failed:", e)

    return _VOICE_ID


def _tts_worker():
    """Background thread: pulls messages from queue and speaks them sequentially."""
    while True:
        item = _speech_queue.get()
        if item is _SENTINEL:
            _speech_queue.task_done()
            break
        try:
            if is_muted():
                emit_event("SPEAK_END", {})
                continue
            speak_start = __import__("time").perf_counter()
            emit_event("SPEAK_START", {})
            engine = pyttsx3.init()
            if _VOICE_ID:
                engine.setProperty("voice", _VOICE_ID)
            engine.say(item)
            engine.runAndWait()
            engine.stop()
            del engine
            elapsed_ms = int((__import__("time").perf_counter() - speak_start) * 1000)
            emit_event("TIMING", {"label": "speak_time", "elapsed_ms": elapsed_ms})
        except Exception as e:
            safe_log("DEBUG -> TTS playback failed:", e)
        finally:
            emit_event("SPEAK_END", {})
            _speech_queue.task_done()


_resolve_voice_id()
_worker_thread = threading.Thread(target=_tts_worker, daemon=True)
_worker_thread.start()


def speak(text, max_chars=300):
    """Queue text for background TTS. Returns immediately."""
    message = (text or "").strip()
    if not message:
        return
    message = message[:max_chars]
    safe_log("SPEAK ->", message)
    _speech_queue.put(message)


def speak_blocking(text, max_chars=300):
    """Speak and block until audio finishes (for wake greeting, bye, etc.)."""
    speak(text, max_chars=max_chars)
    _speech_queue.join()


def flush_speech():
    """Block until all queued speech is done."""
    _speech_queue.join()
