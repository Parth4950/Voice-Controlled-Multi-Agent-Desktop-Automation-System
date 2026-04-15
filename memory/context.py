import json
import os
from datetime import datetime, timezone

CONTEXT_FILE = os.path.join(os.path.dirname(__file__), "context.json")
_HISTORY_LIMIT = 8
_STALENESS_SECONDS = 3600  # 1 hour

context = {
    "last_command": None,
    "last_response": None,
    "last_screen_text": None,
    "current_task": "general usage",
    "last_updated_at": None,
    "history": [],
}


def _load_from_disk():
    """Load persisted context on startup; clear if stale (>1 hour old)."""
    if not os.path.exists(CONTEXT_FILE):
        return
    try:
        with open(CONTEXT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        last = data.get("last_updated_at")
        if last:
            then = datetime.fromisoformat(last)
            age = (datetime.now(timezone.utc) - then).total_seconds()
            if age > _STALENESS_SECONDS:
                return
        for key in ("last_command", "last_response", "last_screen_text", "current_task", "last_updated_at"):
            if key in data:
                context[key] = data[key]
        context["history"] = list(data.get("history", []))[-_HISTORY_LIMIT:]
    except Exception:
        pass


def _save_to_disk():
    try:
        with open(CONTEXT_FILE, "w", encoding="utf-8") as f:
            json.dump(context, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


_load_from_disk()


def update_context(command=None, response=None, screen_text=None):
    timestamp = datetime.now(timezone.utc).isoformat()
    if command is not None:
        context["last_command"] = command
    if response is not None:
        context["last_response"] = response
    if screen_text is not None:
        context["last_screen_text"] = screen_text
    context["last_updated_at"] = timestamp

    entry = {
        "timestamp": timestamp,
        "command": command,
        "response": response[:300] if response else None,
    }
    context["history"].append(entry)
    if len(context["history"]) > _HISTORY_LIMIT:
        context["history"] = context["history"][-_HISTORY_LIMIT:]

    _save_to_disk()


def get_context():
    return {
        "last_command": context["last_command"],
        "last_response": context["last_response"],
        "last_screen_text": context["last_screen_text"],
        "current_task": context.get("current_task") or "general usage",
        "last_updated_at": context["last_updated_at"],
        "history": list(context["history"]),
    }


def set_current_task(task):
    cleaned = (task or "").strip()
    context["current_task"] = cleaned or "general usage"
    context["last_updated_at"] = datetime.now(timezone.utc).isoformat()
    _save_to_disk()


def get_current_task():
    task = context.get("current_task")
    return task if task else "general usage"


def format_context():
    """Render conversation history as human-readable text for Gemini."""
    history = context.get("history", [])
    if not history:
        return "(No previous conversation)"

    lines = ["[Recent conversation]"]
    for entry in history:
        cmd = entry.get("command")
        resp = entry.get("response")
        if cmd:
            lines.append(f"User: {cmd}")
        if resp:
            short = resp[:200] + "..." if len(resp) > 200 else resp
            lines.append(f"Bruh: {short}")
    return "\n".join(lines)
