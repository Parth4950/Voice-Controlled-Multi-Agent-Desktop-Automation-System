import threading


_lock = threading.Lock()
_muted = False
_wake_enabled = True
_push_to_talk_requested = False
_restart_requested = False


def is_muted() -> bool:
    with _lock:
        return _muted


def set_muted(value: bool) -> None:
    global _muted
    with _lock:
        _muted = bool(value)


def is_wake_enabled() -> bool:
    with _lock:
        return _wake_enabled


def set_wake_enabled(value: bool) -> None:
    global _wake_enabled
    with _lock:
        _wake_enabled = bool(value)


def request_push_to_talk() -> None:
    global _push_to_talk_requested
    with _lock:
        _push_to_talk_requested = True


def consume_push_to_talk() -> bool:
    global _push_to_talk_requested
    with _lock:
        value = _push_to_talk_requested
        _push_to_talk_requested = False
        return value


def request_restart() -> None:
    global _restart_requested
    with _lock:
        _restart_requested = True


def consume_restart_request() -> bool:
    global _restart_requested
    with _lock:
        value = _restart_requested
        _restart_requested = False
        return value
