import json
import os
import re
import time

import requests

from context.screen import capture_region_around_cursor
from memory.context import get_current_task, update_context
from ui.event_bus import emit_event

_UI_TUTOR_TIMEOUT = 3.8
_UI_TUTOR_MAX_TOKENS = 180
_FALLBACK = "I can't clearly identify that. Try pointing more precisely."


def _vision_model_chain():
    primary = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
    defaults = ["gemini-2.5-flash", "gemini-2.0-flash"]
    extra = os.getenv("GEMINI_MODEL_FALLBACKS", "").strip()
    tail = [m.strip() for m in extra.split(",") if m.strip()] if extra else defaults
    out = []
    seen = set()
    for item in [primary] + tail:
        if item not in seen:
            out.append(item)
            seen.add(item)
    return out


def _base_output():
    return {
        "element": "unknown",
        "software": "unknown",
        "explanation": _FALLBACK,
        "usage": "Point at a clearer UI element and try again.",
        "recommendation": "Try again with a more precise cursor position.",
        "confidence": "low",
    }


def _normalize_confidence(value):
    v = (value or "").strip().lower()
    if v in {"high", "medium", "low"}:
        return v
    if "high" in v:
        return "high"
    if "medium" in v:
        return "medium"
    return "low"


def _extract_json(text):
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", text or "")
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def _extract_label_value(text, label):
    m = re.search(rf"{label}\s*:\s*(.+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _normalize_output(raw_text):
    data = _base_output()
    parsed = _extract_json(raw_text)
    if isinstance(parsed, dict):
        for key in ("element", "software", "explanation", "usage", "recommendation"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                data[key] = value.strip()
        data["confidence"] = _normalize_confidence(parsed.get("confidence"))
        return data

    text = raw_text or ""
    data["element"] = _extract_label_value(text, "element") or data["element"]
    data["software"] = _extract_label_value(text, "software") or data["software"]
    data["explanation"] = _extract_label_value(text, "explanation") or data["explanation"]
    data["usage"] = _extract_label_value(text, "usage") or data["usage"]
    data["recommendation"] = _extract_label_value(text, "recommendation") or data["recommendation"]
    data["confidence"] = _normalize_confidence(_extract_label_value(text, "confidence"))
    return data


def _build_speech(data):
    element = data.get("element", "that")
    explanation = data.get("explanation", "").strip()
    if explanation:
        short = explanation[:72].rstrip(". ")
        return f"That's {element}. {short}."
    return f"That's {element}."


def _call_gemini_vision(prompt, image_base64, mime_type):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None

    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type, "data": image_base64}},
                ]
            }
        ],
        "generationConfig": {
            "maxOutputTokens": _UI_TUTOR_MAX_TOKENS,
            "temperature": 0.2,
            "topP": 0.8,
        },
    }

    for model in _vision_model_chain():
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            r = requests.post(url, headers=headers, json=body, timeout=_UI_TUTOR_TIMEOUT)
            if not r.ok:
                continue
            payload = r.json()
            candidates = payload.get("candidates") or []
            if not candidates:
                continue
            parts = candidates[0].get("content", {}).get("parts", [])
            text_bits = [p.get("text", "") for p in parts if isinstance(p, dict)]
            final = "\n".join([t for t in text_bits if t]).strip()
            if final:
                return final
        except Exception:
            continue
    return None


def handle_ui_tutor(command=None):
    t0 = time.perf_counter()
    task = get_current_task()
    capture = capture_region_around_cursor(size=350)

    prompt = f"""You are an expert UI tutor.

The user is currently working on: {task}

You are given a cropped image of a UI. The center of the image is where the cursor is pointing.

Your job:

1. Identify the UI element near the center
2. Guess what software this might be (if possible)
3. Explain what this element does (practically)
4. Explain how it is used
5. Tell the user if they should use it RIGHT NOW based on their task

Be concise, practical, and confident.
If unsure, give your best guess but mention uncertainty."""

    raw = _call_gemini_vision(prompt, capture.get("image_base64", ""), capture.get("mime_type", "image/jpeg"))
    result = _normalize_output(raw)

    if not raw or result["confidence"] == "low":
        result = _base_output()

    speech = _build_speech(result)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    result["speech"] = speech
    result["elapsed_ms"] = elapsed_ms

    emit_event(
        "UI_TUTOR_POPUP",
        {
            "cursor": capture.get("cursor", {}),
            "element": result["element"],
            "explanation": result["explanation"],
            "recommendation": result["recommendation"],
            "confidence": result["confidence"],
        },
    )
    emit_event("TIMING", {"label": "ui_tutor", "elapsed_ms": elapsed_ms})

    update_context(command=command or "ui tutor", response=speech)
    return result
