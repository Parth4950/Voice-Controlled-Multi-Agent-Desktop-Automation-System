import os

import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

_DEFAULT_MODEL = "gemini-2.5-flash"
# Tried in order: primary (GEMINI_MODEL) then these until one succeeds.
_DEFAULT_FALLBACKS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
]


def _model_chain():
    primary = os.getenv("GEMINI_MODEL", _DEFAULT_MODEL).strip() or _DEFAULT_MODEL
    extra = os.getenv("GEMINI_MODEL_FALLBACKS", "").strip()
    if extra:
        fallbacks = [m.strip() for m in extra.split(",") if m.strip()]
    else:
        fallbacks = list(_DEFAULT_FALLBACKS)
    seen = set()
    ordered = []
    for m in [primary] + fallbacks:
        if m not in seen:
            seen.add(m)
            ordered.append(m)
    return ordered


def ask_gemini(prompt):
    if not API_KEY:
        print("ERROR in Gemini: GEMINI_API_KEY is not set")
        return "Brain's offline. API key missing."

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": API_KEY,
    }
    data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                ],
            },
        ],
    }

    last_status = None
    last_detail = ""

    for model in _model_chain():
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
        )
        try:
            print("DEBUG -> Gemini trying model:", model)
            response = requests.post(url, headers=headers, json=data, timeout=10)
            last_status = response.status_code

            if response.status_code in (404, 429):
                last_detail = response.text[:400]
                print(
                    f"DEBUG -> Gemini {model} -> HTTP {response.status_code}, "
                    "trying next model if any"
                )
                continue

            if not response.ok:
                last_detail = response.text[:400]
                raise RuntimeError(f"HTTP {response.status_code}: {last_detail}")

            result = response.json()

            if "error" in result:
                err = result["error"]
                code = err.get("code") or err.get("status")
                if code in (404, 429, "NOT_FOUND", "RESOURCE_EXHAUSTED"):
                    last_detail = str(err)[:400]
                    print(f"DEBUG -> Gemini {model} API error {code}, trying next model")
                    continue
                raise RuntimeError(str(err))

            candidates = result.get("candidates") or []
            if not candidates:
                print(f"DEBUG -> Gemini {model}: empty candidates, fast-failing")
                return "Couldn't come up with anything."

            text = candidates[0]["content"]["parts"][0]["text"]
            print("DEBUG -> Gemini response:", text)
            print("DEBUG -> Gemini succeeded with model:", model)
            return text

        except requests.RequestException as e:
            print("ERROR in Gemini (network):", str(e))
            return "Network's down. Can't think right now."

    if last_status == 429:
        msg = (
            "Google AI quota is exhausted or not enabled for your key (limit 0 on free tier). "
            "Open Google AI Studio, enable billing or a paid plan, or set GEMINI_MODEL in .env "
            "to a model your project allows."
        )
        print("ERROR in Gemini:", last_detail or msg)
        return msg

    print("ERROR in Gemini: all models failed.", last_detail)
    return "Brain glitch. Try again."
