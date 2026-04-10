# Voice-Controlled Multi-Agent Desktop Automation System

Jarvis-style Python desktop assistant that listens for a wake word, routes intent, and executes tasks across apps and web.

## Features

- Voice input with wake-word gating (`bro`)
- Voice output using text-to-speech
- Intent routing (`open`, `search`, `play`, memory commands)
- App control (Chrome, Notepad, Calculator, Explorer, VS Code, Spotify)
- Fast web execution for search and media
- Advanced Selenium web automation path with safe fallback
- Simple memory layer (`remember` / `recall`)

## Project Structure

- `main.py` - voice loop, wake-word handling, routing and execution
- `agents/` - router and execution logic
- `tools/` - system tools, browser automation setup
- `voice/` - speech input/output utilities
- `memory/` - persistent JSON memory helpers

## Run

Use your project virtual environment Python:

```powershell
& "c:/Project Bruh/venv/Scripts/python.exe" "c:/Project Bruh/main.py"
```

## Notes

- For voice input, install microphone dependencies (e.g., `pyaudio`) in your venv.
- For Selenium automation, keep Chrome/driver versions compatible.
