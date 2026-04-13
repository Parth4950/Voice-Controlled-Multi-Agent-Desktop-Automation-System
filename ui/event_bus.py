import queue
import time
from typing import Any, Dict, List


_event_queue: "queue.Queue[Dict[str, Any]]" = queue.Queue()


def emit_event(event_type: str, payload: Any = None) -> None:
    try:
        _event_queue.put_nowait(
            {
                "type": str(event_type),
                "payload": payload,
                "ts": time.time(),
            }
        )
    except Exception:
        pass


def consume_events(max_items: int = 200) -> List[Dict[str, Any]]:
    out = []
    for _ in range(max_items):
        try:
            out.append(_event_queue.get_nowait())
        except queue.Empty:
            break
        except Exception:
            break
    return out
