import json
import math
import threading
import time
from datetime import datetime

from ui.event_bus import consume_events, emit_event
from ui.state import (
    is_muted,
    is_wake_enabled,
    request_push_to_talk,
    request_restart,
    set_muted,
    set_wake_enabled,
)


_ui_started = False
_ui_lock = threading.Lock()


def start_overlay() -> None:
    global _ui_started
    with _ui_lock:
        if _ui_started:
            return
        _ui_started = True
    t = threading.Thread(target=_run_ui_thread, daemon=True)
    t.start()


def _run_ui_thread() -> None:
    try:
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
        from PySide6.QtWidgets import (
            QApplication,
            QHBoxLayout,
            QLabel,
            QPushButton,
            QVBoxLayout,
            QWidget,
        )
    except Exception:
        return

    class OrbWidget(QWidget):
        """Asymmetric energy waveform ring (no perfect circles)."""

        _DEG_STEP = 3

        def __init__(self):
            super().__init__()
            self.setMinimumSize(170, 170)
            self._time = 0.0
            self._noise_phase = 0.0
            self.mode = "IDLE"
            self.muted = False
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._tick)
            self._timer.start(16)

        def set_mode(self, mode: str, muted: bool):
            self.mode = mode.upper()
            self.muted = muted

        def _mode_params(self):
            """Return (time_delta, amp_scale, speed_scale, chaos) per mode."""
            if self.mode == "SPEAKING":
                return 0.055, 1.35, 1.65, 1.0
            if self.mode == "THINKING":
                return 0.042, 0.95, 1.15, 0.55
            if self.mode == "LISTENING":
                return 0.032, 0.62, 0.85, 0.25
            return 0.022, 0.38, 0.55, 0.12

        def _tick(self):
            dt, _, speed_scale, _ = self._mode_params()
            self._time += dt * speed_scale
            self._noise_phase += dt * (1.7 + speed_scale * 0.4)
            self.update()

        def _distortion(self, angle_rad: float, t: float, chaos: float) -> float:
            """Multi-frequency asymmetric distortion (never perfectly symmetric)."""
            a = angle_rad
            d = (
                math.sin(a * 3.0 + t * 2.0) * 6.0
                + math.sin(a * 7.0 + t * 1.3) * 4.0
                + math.sin(a * 11.0 + t * 0.7) * 3.0
                + math.sin(a * 0.47 + t * 0.35 + 1.1) * 2.2
            )
            if chaos > 0.01:
                d += chaos * (
                    math.sin(a * 19.0 + t * 2.8) * 2.5
                    + math.sin(a * 29.0 - t * 1.2) * 1.8
                )
            n = (
                math.sin(a * 17.3 + self._noise_phase * 2.1) * 1.1
                + math.sin(a * 23.7 + t * 3.2) * 0.75
                + math.sin(a * 41.0 + t * 59.17) * 0.45 * chaos
            )
            return d + n

        def _build_ring_path(self, cx: float, cy: float, base_r: float, scale: float) -> QPainterPath:
            path = QPainterPath()
            _, amp_scale, _, chaos = self._mode_params()
            if self.muted:
                amp_scale *= 0.42
            t = self._time
            first = True
            for deg in range(0, 360, self._DEG_STEP):
                a = math.radians(deg)
                dist = self._distortion(a, t, chaos) * amp_scale * scale
                r = base_r + dist
                x = cx + r * math.cos(a)
                y = cy + r * math.sin(a)
                if first:
                    path.moveTo(x, y)
                    first = False
                else:
                    path.lineTo(x, y)
            path.closeSubpath()
            return path

        def paintEvent(self, _event):
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing, True)
            p.fillRect(self.rect(), QColor(0, 0, 0, 0))

            cx = self.width() / 2.0
            cy = self.height() / 2.0
            base = min(self.width(), self.height()) * 0.30

            teal = QColor(0, 229, 255)

            glow_layers = [
                (1.14, 10, 22),
                (1.09, 7, 38),
                (1.05, 4, 70),
                (1.0, 2, 200),
            ]

            for scale_off, pen_w, alpha in glow_layers:
                alpha_eff = int(alpha * (0.35 if self.muted else 1.0))
                ring_path = self._build_ring_path(cx, cy, base * scale_off, 1.0)
                pen = QPen(QColor(teal.red(), teal.green(), teal.blue(), alpha_eff))
                pen.setWidth(pen_w)
                pen.setJoinStyle(Qt.RoundJoin)
                p.setBrush(Qt.NoBrush)
                p.setPen(pen)
                p.drawPath(ring_path)

            core_scale = 0.38
            core_path = self._build_ring_path(cx, cy, base * core_scale, 0.55)
            core_alpha = 95 if self.muted else 175
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(20, 200, 255, core_alpha))
            p.drawPath(core_path)

    class OverlayWindow(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
            self.setAttribute(Qt.WA_TranslucentBackground, True)
            self.resize(360, 560)
            self.move(40, 80)

            self.session_active = False
            self.state = "IDLE"
            self.logs = []
            self.transcripts = []
            self.timings = {}
            self.drag_pos = None

            root = QVBoxLayout(self)
            root.setContentsMargins(16, 16, 16, 16)
            root.setSpacing(8)

            self.card = QWidget(self)
            self.card.setStyleSheet(
                "background-color: rgba(8, 14, 22, 230);"
                "border: 1px solid rgba(80, 180, 255, 90); border-radius: 18px;"
            )
            card_layout = QVBoxLayout(self.card)
            card_layout.setContentsMargins(16, 16, 16, 16)
            card_layout.setSpacing(10)
            root.addWidget(self.card)

            title = QLabel("BRUH OVERLAY")
            title.setStyleSheet("color: #9fdfff; font-weight: 700; letter-spacing: 1px;")
            card_layout.addWidget(title, alignment=Qt.AlignHCenter)

            self.orb = OrbWidget()
            card_layout.addWidget(self.orb, alignment=Qt.AlignHCenter)

            self.status = QLabel("Idle")
            self.status.setFont(QFont("Segoe UI", 12, QFont.Bold))
            self.status.setStyleSheet("color: #8ed7ff;")
            card_layout.addWidget(self.status, alignment=Qt.AlignHCenter)

            self.heard = QLabel("Heard: -")
            self.heard.setWordWrap(True)
            self.heard.setStyleSheet("color: rgba(210, 235, 255, 180);")
            card_layout.addWidget(self.heard)

            self.bruh = QLabel("Bruh: -")
            self.bruh.setWordWrap(True)
            card_layout.addWidget(self.bruh)
            self._update_bruh_text_style()

            controls = QHBoxLayout()
            controls.setSpacing(6)
            card_layout.addLayout(controls)

            self.ptt_btn = QPushButton("PTT")
            self.mute_btn = QPushButton("Mute")
            self.wake_btn = QPushButton("Wake: On")
            self.restart_btn = QPushButton("Restart")
            self.export_btn = QPushButton("Export")
            for b in (self.ptt_btn, self.mute_btn, self.wake_btn, self.restart_btn, self.export_btn):
                b.setStyleSheet(
                    "QPushButton {background: rgba(19, 33, 48, 210); color: #9fdfff; "
                    "border: 1px solid rgba(70, 170, 255, 120); border-radius: 10px; padding: 6px;}"
                    "QPushButton:hover {background: rgba(30, 56, 84, 220);}"
                )
                controls.addWidget(b)

            self.timing_label = QLabel("Router: - | OCR: - | Gemini: - | Speak: -")
            self.timing_label.setWordWrap(True)
            self.timing_label.setStyleSheet("color: rgba(160, 210, 255, 160); font-size: 11px;")
            card_layout.addWidget(self.timing_label)

            self.log_label = QLabel("Log: ready")
            self.log_label.setWordWrap(True)
            self.log_label.setStyleSheet("color: rgba(185, 210, 235, 150); font-size: 10px;")
            card_layout.addWidget(self.log_label)

            self.ptt_btn.clicked.connect(self._on_ptt)
            self.mute_btn.clicked.connect(self._on_mute)
            self.wake_btn.clicked.connect(self._on_wake)
            self.restart_btn.clicked.connect(self._on_restart)
            self.export_btn.clicked.connect(self._on_export)

            self._event_timer = QTimer(self)
            self._event_timer.timeout.connect(self._drain_events)
            self._event_timer.start(60)

        def _on_ptt(self):
            request_push_to_talk()
            self._append_log("PTT requested")

        def _on_mute(self):
            next_value = not is_muted()
            set_muted(next_value)
            self.mute_btn.setText("Unmute" if next_value else "Mute")
            self._append_log("Muted" if next_value else "Unmuted")
            self._update_bruh_text_style()
            emit_event("MUTE_CHANGED", {"muted": next_value})

        def _on_wake(self):
            next_value = not is_wake_enabled()
            set_wake_enabled(next_value)
            self.wake_btn.setText("Wake: On" if next_value else "Wake: Off")
            self._append_log("Wake enabled" if next_value else "Wake disabled")
            emit_event("WAKE_CHANGED", {"enabled": next_value})

        def _on_restart(self):
            request_restart()
            self.transcripts.clear()
            self.heard.setText("Heard: -")
            self.bruh.setText("Bruh: -")
            self._append_log("Restart requested")
            emit_event("TRANSCRIPT_CLEAR", {})

        def _on_export(self):
            data = {
                "exported_at": datetime.now().isoformat(),
                "state": self.state,
                "session_active": self.session_active,
                "muted": is_muted(),
                "transcripts": self.transcripts[-10:],
                "timings": self.timings,
                "events": self.logs[-200:],
            }
            path = f"bruh_ui_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                self._append_log(f"Exported: {path}")
            except Exception as e:
                self._append_log(f"Export failed: {e}")

        def _append_log(self, text: str):
            self.logs.append({"ts": time.time(), "text": text})
            self.logs = self.logs[-300:]
            self.log_label.setText(f"Log: {text}")

        def _set_state(self, value: str):
            self.state = value.upper()
            self.status.setText(self.state.title())
            self.orb.set_mode(self.state, is_muted())

        def _update_bruh_text_style(self):
            if is_muted():
                self.bruh.setStyleSheet("color: rgba(220, 245, 255, 250); font-weight: 700;")
            else:
                self.bruh.setStyleSheet("color: rgba(220, 245, 255, 150);")
            self.orb.set_mode(self.state, is_muted())

        def _update_timing_line(self):
            def g(key):
                v = self.timings.get(key)
                return "-" if v is None else f"{v}ms"

            self.timing_label.setText(
                f"Router: {g('router_time')} | OCR: {g('screen_ocr')} | "
                f"Gemini: {g('screen_gemini')} | Speak: {g('speak_time')}"
            )

        def _handle_event(self, ev):
            t = ev.get("type")
            payload = ev.get("payload")
            if t == "STATE_CHANGE":
                self._set_state(str(payload))
            elif t == "SESSION_ACTIVE":
                self.session_active = bool(payload)
                if not self.session_active:
                    self._set_state("IDLE")
            elif t == "USER_TEXT":
                text = (payload or {}).get("text", "")
                if text:
                    self.heard.setText(f"Heard: {text}")
                    self.transcripts.append({"user": text, "at": ev.get("ts")})
            elif t == "AI_RESPONSE":
                text = (payload or {}).get("text", "")
                if text:
                    self.bruh.setText(f"Bruh: {text}")
                    if self.transcripts:
                        self.transcripts[-1]["bruh"] = text
                    else:
                        self.transcripts.append({"user": "", "bruh": text, "at": ev.get("ts")})
                    self.transcripts = self.transcripts[-10:]
            elif t == "TIMING":
                label = (payload or {}).get("label")
                elapsed = (payload or {}).get("elapsed_ms")
                if label is not None and elapsed is not None:
                    self.timings[str(label)] = int(elapsed)
                    self._update_timing_line()
            elif t == "SPEAK_START":
                self._set_state("SPEAKING")
            elif t == "SPEAK_END":
                self._set_state("LISTENING" if self.session_active else "IDLE")

        def _drain_events(self):
            for ev in consume_events():
                self._handle_event(ev)

        def mousePressEvent(self, event):
            if event.button() == Qt.LeftButton:
                self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

        def mouseMoveEvent(self, event):
            if self.drag_pos is not None and event.buttons() & Qt.LeftButton:
                self.move(event.globalPosition().toPoint() - self.drag_pos)

        def mouseReleaseEvent(self, _event):
            self.drag_pos = None

    app = QApplication([])
    win = OverlayWindow()
    win.show()
    app.exec()
