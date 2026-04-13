import speech_recognition as sr
import time

_MIC_ERROR_SHOWN = False
_LAST_ERROR_AT = 0.0

PAUSE_THRESHOLD = 1.5
NON_SPEAKING_DURATION = 0.5
LISTEN_TIMEOUT = 8
PHRASE_TIME_LIMIT = 15
AMBIENT_DURATION = 1.2

WAKE_TIMEOUT = 3
WAKE_PHRASE_LIMIT = 4

_RECALIBRATE_EVERY = 30

_recognizer = sr.Recognizer()
_recognizer.pause_threshold = PAUSE_THRESHOLD
_recognizer.non_speaking_duration = NON_SPEAKING_DURATION
_recognizer.dynamic_energy_threshold = False
_calibrated = False
_listen_count = 0


def _maybe_calibrate(source):
    """Calibrate mic if needed; shared by both listeners."""
    global _calibrated, _listen_count
    needs_cal = not _calibrated or (_listen_count % _RECALIBRATE_EVERY == 0)
    if needs_cal:
        print("Calibrating microphone...")
        _recognizer.adjust_for_ambient_noise(source, duration=AMBIENT_DURATION)
        _calibrated = True
    _listen_count += 1


def listen_for_wake_word():
    """Lightweight listener that only waits for 'hey bro'. Short timeouts, no 'Listening...' spam."""
    global _calibrated, _MIC_ERROR_SHOWN, _LAST_ERROR_AT
    try:
        with sr.Microphone() as source:
            _maybe_calibrate(source)
            audio = _recognizer.listen(
                source, timeout=WAKE_TIMEOUT, phrase_time_limit=WAKE_PHRASE_LIMIT,
            )
    except sr.WaitTimeoutError:
        return None
    except Exception:
        _calibrated = False
        return None

    try:
        text = _recognizer.recognize_google(audio).lower().strip()
        if "hey bro" in text:
            return text
    except Exception:
        pass
    return None


def listen_command():
    global _MIC_ERROR_SHOWN, _LAST_ERROR_AT, _calibrated

    try:
        with sr.Microphone() as source:
            _maybe_calibrate(source)
            print("Listening...")
            audio = _recognizer.listen(source, timeout=LISTEN_TIMEOUT, phrase_time_limit=PHRASE_TIME_LIMIT)
    except sr.WaitTimeoutError:
        return {"status": "no_speech", "text": ""}
    except Exception:
        now = time.time()
        if not _MIC_ERROR_SHOWN or (now - _LAST_ERROR_AT) > 30:
            print("Microphone is not available. Install PyAudio to use voice input.")
            _MIC_ERROR_SHOWN = True
            _LAST_ERROR_AT = now
        _calibrated = False
        return {"status": "mic_unavailable", "text": ""}

    try:
        text = _recognizer.recognize_google(audio)
        return {"status": "ok", "text": text.lower().strip()}
    except sr.UnknownValueError:
        return {"status": "unrecognized", "text": ""}
    except sr.RequestError:
        return {"status": "service_error", "text": ""}
    except Exception:
        return {"status": "unrecognized", "text": ""}
