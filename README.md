# Project Bruh — Voice-Controlled Desktop Assistant

A fast, personality-driven Windows desktop assistant that listens for a wake word, routes intent, and executes tasks across apps and the web.

## Features

- **Voice input** with wake-word gating (`hey bro`), ambient noise calibration, idle recovery
- **Voice output** via `pyttsx3` with configurable voice selection
- **Deterministic router** for open/launch/search/play/close/volume/screenshot — no AI on the fast path
- **AI path** via Gemini for general knowledge, code help, and context-aware answers
- **Bruh personality** baked into all AI responses (sarcastic, direct, helpful)
- **App control** — open *and close* apps (Chrome, Notepad, Calculator, Spotify, VS Code, etc.)
- **Volume control** — up, down, mute via voice
- **Screenshot on demand** — "take a screenshot"
- **Playwright browser automation** for YouTube with guaranteed direct-URL fallback
- **Memory** — persistent `remember` / `recall` with fuzzy matching
- **Bounded context** — last 5 interactions for follow-up awareness
- **Safe logging** — no Unicode crashes on Windows
- **Graceful shutdown** — Playwright browser cleaned up on Ctrl+C / exit
- **Smoke tests** for regression safety

## Project Structure

```
main.py              — voice loop, wake-word handling, routing, execution
agents/
  router.py          — deterministic intent matching
  planner.py         — AI agent selector
  dispatcher.py      — agent dispatch
  execution.py       — intent → tool execution
  personality.py     — shared Bruh system prompt
  web_agent.py       — general knowledge via Gemini
  code_agent.py      — code help via screen OCR + Gemini
  system_agent.py    — open/close apps
  automation_agent.py — Playwright YouTube automation
  memory_agent.py    — remember/recall interface
tools/
  system_tools.py    — open/close app, search, play, volume, screenshot
  browser.py         — Playwright lifecycle and page helpers
  log.py             — safe_log, timing utilities
voice/
  input.py           — microphone + Google STT
  output.py          — pyttsx3 TTS with voice_config.json support
  voice_selector.py  — interactive voice picker
memory/
  memory.py          — JSON key-value store with fuzzy recall
  context.py         — bounded session context
context/
  screen.py          — screenshot + OCR via pytesseract
tests/
  test_smoke.py      — smoke tests
```

## Setup

1. **Create a virtual environment:**
   ```powershell
   python -m venv venv
   ```

2. **Install dependencies:**
   ```powershell
   & "c:/Project Bruh/venv/Scripts/pip.exe" install -r requirements.txt
   ```

3. **Install Playwright browsers:**
   ```powershell
   & "c:/Project Bruh/venv/Scripts/playwright.exe" install chromium
   ```

4. **Set your Gemini API key** in a `.env` file:
   ```
   GEMINI_API_KEY=your_key_here
   ```

5. **Microphone:** Ensure PyAudio is installed and a microphone is available.

6. **Tesseract OCR (optional):** Install [Tesseract](https://github.com/tesseract-ocr/tesseract) for screen reading features.

## Run

```powershell
& "c:/Project Bruh/venv/Scripts/python.exe" "c:/Project Bruh/main.py"
```

Say **"hey bro"** to start a session, then give commands like:
- "open chrome"
- "search latest news"
- "play lofi beats"
- "close notepad"
- "volume up"
- "take a screenshot"
- "remember my favorite color is blue"
- "what is my favorite color"
- "bye" to end session

## Smoke Tests

```powershell
& "c:/Project Bruh/venv/Scripts/python.exe" -m pytest tests/ -v
```

Or with unittest:
```powershell
& "c:/Project Bruh/venv/Scripts/python.exe" "c:/Project Bruh/tools/scripts/smoke_check.py"
```
