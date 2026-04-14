import atexit
import signal
import os as _os

from agents.router import route_command
from agents.execution import execute
from agents.planner import plan_task
from agents.dispatcher import dispatch
import time
from voice.input import listen_command, listen_for_wake_word
from voice.output import speak, speak_blocking, flush_speech
from tools.log import safe_log, now_ms, log_timing
from tools.browser import close_browser
from memory.context import update_context
from ui.event_bus import emit_event
from ui.overlay import start_overlay
from ui.state import consume_push_to_talk, consume_restart_request, is_wake_enabled

_LOCK_FILE = _os.path.join(_os.path.dirname(__file__), ".bruh.lock")


def _check_single_instance():
    """Warn and write lock file."""
    my_pid = _os.getpid()
    if _os.path.exists(_LOCK_FILE):
        try:
            with open(_LOCK_FILE, "r") as f:
                old_pid = int(f.read().strip())
            if old_pid != my_pid:
                print(f"WARNING: Previous Bruh (PID {old_pid}) may still be running.")
                print("Run: Get-Process python* | Stop-Process -Force")
        except Exception:
            pass
    with open(_LOCK_FILE, "w") as f:
        f.write(str(my_pid))


_check_single_instance()


def _cleanup():
    safe_log("DEBUG -> Cleaning up browser on exit")
    try:
        close_browser()
    except Exception:
        pass
    try:
        if _os.path.exists(_LOCK_FILE):
            _os.remove(_LOCK_FILE)
    except Exception:
        pass


atexit.register(_cleanup)

for sig in (signal.SIGINT, signal.SIGTERM):
    try:
        signal.signal(sig, lambda *_: (_cleanup(), exit(0)))
    except (OSError, ValueError):
        pass


def _fast_path_feedback(intent, result):
    """Map fast-path execute() results to short spoken feedback."""
    if intent == "open_app":
        return "Done" if result else "Couldn't open that"
    if intent == "close_app":
        return "Closed" if result else "Couldn't close that"
    if intent == "volume":
        return str(result) if result else None
    if intent == "screenshot":
        return "Screenshot saved" if result and "failed" not in str(result).lower() else "Screenshot failed"
    if intent == "remember":
        return "Got it"
    if intent == "recall":
        return str(result) if result else "I don't remember that"
    if intent == "analyze_context":
        return str(result)[:300] if result else "Couldn't read your screen."
    if intent in ("navigate", "web_click", "web_type", "web_scroll"):
        return str(result) if result else None
    if intent in (
        "create_folder",
        "create_file",
        "fs_copy",
        "fs_move",
        "fs_delete",
        "fs_rename",
        "fs_open",
    ):
        return str(result)[:300] if result else None
    return None


def is_simple_command(command):
    keywords = [
        "open", "launch", "start", "run",
        "search", "google", "look up", "find",
        "play",
        "close", "kill", "quit", "stop", "exit",
        "screenshot",
        "volume", "mute",
        "remember",
        "what is my",
        "go to", "navigate",
        "click", "type", "scroll",
        "create", "make",
        "copy", "move", "cut", "delete", "remove", "trash", "rename", "duplicate",
    ]
    screen_triggers = [
        "on my screen", "on screen", "looking at", "this code", "the code",
        "my screen", "what do you see", "what am i looking", "read my screen",
        "see my screen", "what app is open", "what is this code", "what is this app",
        "currently on my", "what is on my", "what's on my",
    ]
    if any(command.startswith(k) for k in keywords):
        return True
    if command.startswith("new folder ") or command.startswith("new file "):
        return True
    if any(t in command for t in screen_triggers):
        return True
    return False


session_active = False
empty_in_session_count = 0
wake_started_at = 0
_idle_logged = False

_SINGLE_WORD_OK = {
    "stop", "mute", "screenshot", "bye", "thanks", "yes", "no",
    "news", "weather", "time", "help", "music", "repeat",
}

_INSTANT_REPLIES = {
    "hi": "Yo. What do you need?",
    "hello": "Hey. What's up?",
    "hey": "Sup. What do you want?",
    "how are you": "Alive, unfortunately. What do you need?",
    "what's up": "Your blood pressure, probably. What do you want?",
    "sup": "Nothing much. What do you need?",
    "thanks": "Yeah yeah.",
    "thank you": "Yeah yeah.",
    "good morning": "Morning. What do you need?",
    "good night": "Later.",
    "yo": "Yo. What's up?",
    "wassup": "Not much. What do you need?",
    "who are you": "I'm Bruh. Your desktop overlord.",
    "what are you": "Your worst nightmare with a mic.",
    "you suck": "And you need me. Tragic.",
    "you're useless": "Says the one talking to their computer.",
}

print(f"=== BRUH v2 | PID {_os.getpid()} | {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
safe_log(f"DEBUG -> Process started PID={_os.getpid()}")
start_overlay()
emit_event("STATE_CHANGE", "IDLE")
emit_event("SESSION_ACTIVE", False)

while True:
    try:
        if consume_restart_request():
            session_active = False
            empty_in_session_count = 0
            _idle_logged = False
            emit_event("TRANSCRIPT_CLEAR", {})
            emit_event("SESSION_ACTIVE", False)
            emit_event("STATE_CHANGE", "IDLE")
            safe_log("DEBUG -> Restart requested from UI")
            continue

        # ---- IDLE MODE: lightweight wake-word listener only ----
        if not session_active:
            if not _idle_logged:
                safe_log("DEBUG -> Idle mode, waiting for wake word...")
                _idle_logged = True
            emit_event("STATE_CHANGE", "IDLE")
            ptt_requested = consume_push_to_talk()
            wake = None
            if ptt_requested:
                wake = "ptt"
            elif is_wake_enabled():
                try:
                    wake = listen_for_wake_word()
                except Exception:
                    continue
            else:
                time.sleep(0.1)
            if wake and ("hey bro" in wake or wake == "ptt"):
                session_active = True
                _idle_logged = False
                wake_started_at = now_ms()
                safe_log("DEBUG -> SESSION ACTIVE: True (wake word)")
                speak_blocking("Hey Parth, what can I do for you today?")
                log_timing("wake_to_first_response", wake_started_at)
                emit_event("SESSION_ACTIVE", True)
            continue

        # ---- ACTIVE SESSION: full command processing ----
        emit_event("STATE_CHANGE", "LISTENING")
        try:
            heard = listen_command()
        except Exception:
            continue

        status = (heard or {}).get("status", "unrecognized")
        command = (heard or {}).get("text", "").strip().lower()

        if status in ("mic_unavailable", "service_error"):
            safe_log("DEBUG -> Voice input issue:", status)
            speak("Mic issue detected, still here when you're ready.", max_chars=120)
            time.sleep(1.0)
            continue

        if status in ("no_speech", "unrecognized") or not command:
            empty_in_session_count += 1
            if empty_in_session_count >= 5:
                safe_log("DEBUG -> Session idle due to repeated empty captures")
                speak("Didn't catch that. Say it again, bro.", max_chars=90)
                empty_in_session_count = 0
            continue
        empty_in_session_count = 0

        safe_log("DEBUG -> Heard command:", command)
        emit_event("USER_TEXT", {"text": command})

        if "bye" in command:
            speak_blocking("Alright, see you!")
            session_active = False
            safe_log("DEBUG -> SESSION ACTIVE: False (bye)")
            emit_event("SESSION_ACTIVE", False)
            emit_event("STATE_CHANGE", "IDLE")
            continue

        if len(command.split()) < 2 and command not in _SINGLE_WORD_OK:
            continue

        instant = _INSTANT_REPLIES.get(command)
        if instant:
            safe_log("DEBUG -> Instant reply for:", command)
            speak(instant, max_chars=120)
            update_context(command=command, response=instant)
            continue

        interaction_keywords = ("click", "first", "control", "interact", "automate", "auto")
        has_interaction_step = any(keyword in command for keyword in interaction_keywords)

        safe_log("DEBUG -> Checking fast path")
        cycle_start = now_ms()

        # FAST PATH
        if is_simple_command(command):
            safe_log("DEBUG -> Fast path triggered")
            route_start = now_ms()
            intent, params = route_command(command)
            log_timing("router_time", route_start)

            if intent == "unknown":
                safe_log("DEBUG -> Router returned unknown, falling through to AI path")
            else:
                if intent == "play_media" and has_interaction_step:
                    intent = "play_media_advanced"

                if intent == "analyze_context":
                    emit_event("STATE_CHANGE", "THINKING")
                    speak_blocking("Checking your screen...", max_chars=60)

                action_start = now_ms()
                result = execute(intent, params)
                log_timing("command_to_action_start", action_start)
                log_timing("fast_command_total", cycle_start)

                feedback = _fast_path_feedback(intent, result)
                if not feedback:
                    feedback = "Done."
                speak(
                    feedback,
                    max_chars=260
                    if intent
                    in (
                        "create_folder",
                        "create_file",
                        "fs_copy",
                        "fs_move",
                        "fs_delete",
                        "fs_rename",
                        "fs_open",
                    )
                    else 120,
                )
                emit_event("AI_RESPONSE", {"text": feedback})

                update_context(command=command, response=feedback)
                continue

        # AI PATH
        safe_log("DEBUG -> Going to AI path")
        emit_event("STATE_CHANGE", "THINKING")
        plan_start = now_ms()
        agent = plan_task(command)
        log_timing("planner_time", plan_start)
        valid_agents = {
            "code_agent",
            "web_agent",
            "system_agent",
            "automation_agent",
            "memory_agent",
        }
        if agent not in valid_agents:
            agent = "web_agent"

        safe_log("DEBUG -> Selected agent:", agent)

        if agent == "code_agent":
            speak_blocking("Checking your screen...", max_chars=60)
        elif agent != "memory_agent":
            speak("Hold on...", max_chars=30)

        safe_log("DEBUG -> Dispatching to agent")
        dispatch_start = now_ms()
        response = dispatch(agent, command)
        log_timing("dispatch_time", dispatch_start)

        safe_log("DEBUG -> Response received:", response)

        if not response:
            response = "Got nothing from that. Try again."
        safe_log("Bruh:", response)
        emit_event("AI_RESPONSE", {"text": response})
        speak(response, max_chars=300)
        log_timing("command_to_voice_output", cycle_start)
        log_timing("ai_command_total", cycle_start)

    except Exception as e:
        import traceback
        safe_log("ERROR -> main loop:", e)
        safe_log(traceback.format_exc())
        continue
