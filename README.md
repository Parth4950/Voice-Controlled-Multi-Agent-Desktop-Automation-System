# Project Bruh

Windows voice assistant with deterministic command execution, Gemini-backed AI fallback, browser automation, OCR screen understanding, memory, and filesystem management.

## Highlights

- Wake-word session flow (`hey bro` to activate, `bye` to end)
- Fast path for routine commands (no AI latency)
- AI path for general Q&A and follow-up conversation
- OCR-based screen/context analysis
- Browser automation (navigate/click/type/scroll/YouTube flow)
- Persistent memory (`remember`, `what is my ...`)
- Filesystem operations (create/open/copy/move/rename/delete)
- Overlay/event bus integration and timing logs

## How It Works

Project Bruh routes each spoken command in two stages:

1. **Fast path** (`agents/router.py` + `agents/execution.py`): regex/keyword intent matching and direct tool execution.
2. **AI path** (`agents/planner.py` + agents): heuristic routing and Gemini response generation when no deterministic intent applies.

Runtime orchestration is in `main.py`, which manages wake mode, active session loop, speech I/O, context, and cleanup.

## Current Architecture

```text
main.py
agents/
  router.py            # deterministic intent parsing
  execution.py         # intent handlers and tool calls
  planner.py           # heuristic + Gemini agent selection
  dispatcher.py        # selected-agent dispatch
  web_agent.py         # general Q&A/chat
  code_agent.py        # screen/code-aware responses
  system_agent.py      # app-launch focused handling
  automation_agent.py  # browser automation agent
  memory_agent.py      # memory interactions
  personality.py       # system prompt/persona
tools/
  system_tools.py      # apps, volume, screenshot, search/media helpers
  browser.py           # Playwright helpers/lifecycle
  filesystem_tools.py  # path parsing + filesystem actions
  log.py               # safe logging + timing utilities
voice/
  input.py             # microphone + speech recognition
  output.py            # TTS
  voice_selector.py    # voice setup helper
context/
  screen.py            # screenshot + OCR
memory/
  memory.py            # persistent key-value memory
  context.py           # bounded conversation context
ui/
  overlay.py, state.py, event_bus.py
tests/
  test_smoke.py
```

## Platform + Requirements

- **OS:** Windows (current implementation uses Windows-specific APIs/commands)
- **Python:** 3.10+
- **Mic:** Required for voice input
- **Gemini API key:** Required for AI-path features
- **Tesseract OCR:** Required for screen reading/analysis
- **Playwright Chromium:** Required for browser automation flows

## Setup

1. Create a virtual environment:

```powershell
python -m venv venv
```

2. Install dependencies:

```powershell
.\venv\Scripts\pip.exe install -r requirements.txt
```

3. Install Playwright browser:

```powershell
.\venv\Scripts\playwright.exe install chromium
```

4. Create `.env` in the project root:

```env
GEMINI_API_KEY=your_key_here
```

5. Install Tesseract and verify path in `config.py` (or override via `config.json`).

## Run

```powershell
.\venv\Scripts\python.exe .\main.py
```

## Voice Commands (Current)

### Session

- `hey bro`
- `bye`

### App/System

- `open chrome`
- `launch notepad`
- `close spotify`
- `volume up` / `volume down` / `mute`
- `screenshot`

### Browser/Web

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

### Filesystem

- `create a folder name ghost`
- `create a new file name notes`
- `open folder desktop`
- `open file notes.txt`
- `copy ghost to desktop`
- `move ghost to downloads`
- `rename ghost to ghost_backup`
- `delete ghost`
- `delete the folder ghost` (spoken filler normalized)

## Filesystem Behavior

- Default create root: `Documents\BruhFiles` (override with `bruh_files_root`)
- Aliases supported in path parsing: desktop, documents, downloads, pictures, videos, music, bruh files
- Scope control via `filesystem_scope`:
  - `home`: user profile + Bruh root
  - `full`: full machine path access (with safety checks)
- Safety guards block destructive operations on critical system locations

## Configuration

`config.json` (optional, next to `config.py`) can override defaults. Useful keys:

- `tesseract_cmd`
- `playwright_user_data_dir`
- `app_map`, `app_fallbacks`, `process_map`
- `bruh_files_root`
- `filesystem_scope`

See `config.json.example` for structure.

## Testing

Run smoke tests:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_smoke.py -q
```

Current smoke coverage includes router, planner, execution flows, memory/context, and filesystem operations.

## Troubleshooting

- If wake/voice misses commands: check microphone permissions and ambient noise.
- If AI path fails: verify `GEMINI_API_KEY` and internet connectivity.
- If screen analysis is weak: verify Tesseract install/path.
- If browser actions fail: reinstall Playwright Chromium.
- If filesystem command fails to resolve: try explicit location phrasing (`... in desktop`, `open folder documents`).

## Caution

Filesystem commands can modify/delete local files. Use `filesystem_scope=home` if you want stricter boundaries.
