import sys
import time


def safe_log(*parts):
    """Print to console without ever raising — handles Windows cp1252 encoding issues."""
    try:
        text = " ".join(str(p) for p in parts)
        encoding = getattr(sys.stdout, "encoding", None) or "cp1252"
        sanitized = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(sanitized)
    except Exception:
        pass


def now_ms():
    return int(time.perf_counter() * 1000)


def log_timing(label, start_ms):
    try:
        elapsed = now_ms() - int(start_ms)
        safe_log(f"TIMING -> {label}: {elapsed}ms")
    except Exception:
        pass
