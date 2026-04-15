import threading

from tools.log import safe_log
from ui.state import request_ui_tutor

_started = False
_lock = threading.Lock()


def start_hotkeys() -> None:
    global _started
    with _lock:
        if _started:
            return
        _started = True

    t = threading.Thread(target=_run_listener, daemon=True)
    t.start()


def _run_listener() -> None:
    try:
        from pynput import keyboard
    except Exception as e:
        safe_log("DEBUG -> Hotkeys disabled:", e)
        return

    held = set()

    def on_press(key):
        held.add(key)
        has_ctrl = any(
            k in held
            for k in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r)
        )
        has_shift = any(
            k in held
            for k in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r)
        )
        has_t = (
            keyboard.KeyCode.from_char("t") in held
            or keyboard.KeyCode.from_char("T") in held
        )
        if has_ctrl and has_shift and has_t:
            request_ui_tutor()

    def on_release(key):
        if key in held:
            held.remove(key)

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()
