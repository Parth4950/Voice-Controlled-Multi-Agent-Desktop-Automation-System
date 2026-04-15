# Project Bruh

Project Bruh is a Windows voice-controlled assistant with a deterministic command engine, AI fallback routing, screen-aware reasoning, browser automation, and desktop utility actions.

## Core Capabilities

- Wake-word interaction model (`hey bro` to start, `bye` to end)
- Dual-path execution:
  - **Fast path** for deterministic command handling
  - **AI path** for planning, general reasoning, and fallback handling
- Screen understanding:
  - OCR-based context analysis
  - Universal Tutor Mode for cursor-focused UI guidance
- Browser automation (navigate, click, type, scroll, media workflows)
- Persistent memory and bounded conversational context
- Filesystem operations with scoped safety controls
- Overlay UI with event-driven state/timing visualization

## Universal Tutor Mode (New)

Universal Tutor Mode provides task-aware, cursor-centric UI guidance across desktop software.

### What It Does

- Captures a small region around the cursor (not full-screen)
- Uses Gemini vision to infer:
  - nearby UI element
  - likely software context
  - practical purpose
  - usage guidance
  - task-based recommendation
- Returns structured output with confidence:

```json
{
  "element": "...",
  "software": "...",
  "explanation": "...",
  "usage": "...",
  "recommendation": "...",
  "confidence": "high/medium/low"
}
```

### Triggers

- Voice phrases:
  - `what is this`
  - `what does this do`
  - `explain this`
  - `should i use this`
- Hotkey:
  - `Ctrl + Shift + T`

### Runtime Behavior

- Displays a compact neon-styled popup near cursor with:
  - element
  - explanation
  - recommendation
- Speaks a short summary only
- Uses failsafe output when uncertain:
  - `I can't clearly identify that. Try pointing more precisely.`

## Architecture

Project Bruh follows this runtime flow:

`Voice -> Router -> Planner -> Dispatcher -> Agents -> Execution -> Voice Output`

### Key Components

```text
main.py
agents/
  router.py            # deterministic intent parsing
  planner.py           # heuristic + Gemini agent selection
  dispatcher.py        # selected-agent dispatch
  execution.py         # intent handlers and tool calls
  ui_tutor_agent.py    # cursor-focused UI tutoring (Gemini vision)
  web_agent.py         # general Q&A/chat
  code_agent.py        # code/screen-aware responses
  system_agent.py      # app-launch focused handling
  automation_agent.py  # UI/browser automation handling
  memory_agent.py      # memory interactions
  personality.py       # system prompt/persona
context/
  screen.py            # full screenshot + OCR + cursor-region capture
memory/
  memory.py            # persistent key-value memory
  context.py           # bounded conversation + current_task
ui/
  overlay.py           # floating overlay + tutor popup rendering
  hotkeys.py           # global Ctrl+Shift+T listener
  state.py             # thread-safe UI/runtime flags
  event_bus.py         # cross-thread event transport
tools/
  browser.py
  filesystem_tools.py
  system_tools.py
  log.py
voice/
  input.py             # speech recognition
  output.py            # TTS pipeline
tests/
  test_smoke.py
```

## Requirements

- **OS:** Windows
- **Python:** 3.10+
- **Microphone:** required for voice flow
- **Gemini API key:** required for AI and tutor features
- **Tesseract OCR:** required for OCR screen analysis
- **Playwright Chromium:** required for browser automation

## Setup

1. Create environment:

```powershell
python -m venv venv
```

2. Install dependencies:

```powershell
.\venv\Scripts\pip.exe install -r requirements.txt
```

3. Install browser runtime:

```powershell
.\venv\Scripts\playwright.exe install chromium
```

4. Configure environment:

```env
GEMINI_API_KEY=your_key_here
```

5. Install Tesseract and verify `config.py` / `config.json` path override.

## Run

```powershell
.\venv\Scripts\python.exe .\main.py
```

## Command Reference

### Session

- `hey bro`
- `bye`

### System/App

- `open chrome`
- `launch notepad`
- `close spotify`
- `volume up` / `volume down` / `mute`
- `screenshot`

### Web/Automation

- `search python decorators`
- `go to github.com`
- `click sign in`
- `type hello world`
- `scroll down`
- `open youtube and play lofi`

### Memory

- `remember my favorite color is blue`
- `what is my favorite color`

### Screen Context

- `what am i looking at`
- `what is on my screen`
- `read my screen`

### Universal Tutor

- `what is this`
- `what does this do`
- `explain this`
- `should i use this`
- `Ctrl + Shift + T`

### Filesystem

- `create a folder name ghost`
- `create a new file name notes`
- `open folder desktop`
- `open file notes.txt`
- `copy ghost to desktop`
- `move ghost to downloads`
- `rename ghost to ghost_backup`
- `delete ghost`

## Configuration

`config.json` (optional, next to `config.py`) can override defaults.

Useful keys:

- `tesseract_cmd`
- `playwright_user_data_dir`
- `app_map`, `app_fallbacks`, `process_map`
- `bruh_files_root`
- `filesystem_scope`

`memory/context.py` also persists `current_task` used by Universal Tutor Mode.

## Testing

Run smoke tests:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_smoke.py -q
```

Coverage includes routing, planning, execution, memory/context, tutor integration, and filesystem behaviors.

## Troubleshooting

- Voice reliability issues:
  - verify microphone permissions and ambient noise profile
- Gemini response failures:
  - verify `GEMINI_API_KEY`, internet access, and model availability
- Weak screen interpretation:
  - verify Tesseract install/path and cursor precision
- Browser automation failures:
  - reinstall Playwright Chromium
- Tutor uncertainty:
  - point cursor more precisely and retry

## Safety Note

Filesystem commands can modify or delete local files. Prefer `filesystem_scope=home` unless broader access is explicitly required.
