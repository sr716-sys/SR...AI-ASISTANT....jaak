from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class HealthRecord:
    last_progress_ts: float = field(default_factory=time.monotonic)
    last_progress_kind: str = "init"
    last_tool_call_ts: float = field(default_factory=time.monotonic)
    last_tool_complete_ts: float = field(default_factory=time.monotonic)
    last_receive_ts: float = field(default_factory=time.monotonic)
    last_send_ts: float = field(default_factory=time.monotonic)
    last_screen_capture_ts: float = field(default_factory=time.monotonic)
    last_vision_ts: float = field(default_factory=time.monotonic)
    last_tts_ts: float = field(default_factory=time.monotonic)
    last_voice_input_ts: float = field(default_factory=time.monotonic)
    last_task_transition_ts: float = field(default_factory=time.monotonic)
    last_task_state: str = "IDLE"
    last_exception_ts: float = 0.0
    last_reconnect_ts: float = 0.0
    current_task: str = "IDLE"
    current_session: str = "unknown"
    reconnect_count: int = 0
    exception_count: int = 0
    queue_sizes: dict[str, int] = field(default_factory=dict)
    worker_status: dict[str, Any] = field(default_factory=dict)
    progress_expected: bool = True
    expected_kind: str = ""
    expected_since_ts: float = 0.0
    expected_timeout: float = 0.0

    def note_progress(self, kind: str, *, session: str | None = None, task: str | None = None) -> None:
        now = time.monotonic()
        normalized = kind.strip().lower()
        aliases = {
            "tool": "tool_call",
            "tool_call": "tool_call",
            "tool_complete": "tool_complete",
            "screen": "screen_capture",
            "screen_capture": "screen_capture",
            "vision": "vision",
            "tts": "tts",
            "voice": "voice",
            "receive": "receive",
            "send": "send",
        }
        mapped = aliases.get(normalized, normalized)
        self.last_progress_ts = now
        self.last_progress_kind = mapped
        if mapped == "receive":
            self.last_receive_ts = now
        elif mapped == "send":
            self.last_send_ts = now
        elif mapped == "tool_call":
            self.last_tool_call_ts = now
        elif mapped == "tool_complete":
            self.last_tool_complete_ts = now
        elif mapped == "screen_capture":
            self.last_screen_capture_ts = now
        elif mapped == "vision":
            self.last_vision_ts = now
        elif mapped == "tts":
            self.last_tts_ts = now
        elif mapped == "voice":
            self.last_voice_input_ts = now
        elif mapped == "task_transition":
            self.last_task_transition_ts = now
            if task:
                self.last_task_state = task
        if session:
            self.current_session = session
        if task:
            self.current_task = task

    def set_expectation(self, expected: bool, *, kind: str = "", timeout: float = 0.0) -> None:
        self.progress_expected = expected
        self.expected_kind = kind
        self.expected_since_ts = time.monotonic() if expected else 0.0
        self.expected_timeout = max(0.0, float(timeout))

    def snapshot(self) -> dict:
        return {
            "last_progress_ts": self.last_progress_ts,
            "last_progress_kind": self.last_progress_kind,
            "last_receive_ts": self.last_receive_ts,
            "last_send_ts": self.last_send_ts,
            "last_tool_call_ts": self.last_tool_call_ts,
            "last_tool_complete_ts": self.last_tool_complete_ts,
            "last_screen_capture_ts": self.last_screen_capture_ts,
            "last_vision_ts": self.last_vision_ts,
            "last_tts_ts": self.last_tts_ts,
            "last_voice_input_ts": self.last_voice_input_ts,
            "last_task_transition_ts": self.last_task_transition_ts,
            "last_task_state": self.last_task_state,
            "last_exception_ts": self.last_exception_ts,
            "last_reconnect_ts": self.last_reconnect_ts,
            "current_task": self.current_task,
            "current_session": self.current_session,
            "reconnect_count": self.reconnect_count,
            "exception_count": self.exception_count,
            "queue_sizes": self.queue_sizes.copy(),
            "worker_status": dict(self.worker_status),
            "progress_expected": self.progress_expected,
            "expected_kind": self.expected_kind,
            "expected_since_ts": self.expected_since_ts,
            "expected_timeout": self.expected_timeout,
            "elapsed": self.elapsed(),
        }

    def elapsed(self, now: float | None = None) -> dict[str, float]:
        now = time.monotonic() if now is None else now
        fields = (
            "last_progress_ts", "last_receive_ts", "last_send_ts",
            "last_tool_call_ts", "last_tool_complete_ts",
            "last_screen_capture_ts", "last_vision_ts", "last_tts_ts",
            "last_voice_input_ts", "last_task_transition_ts",
        )
        return {name.removeprefix("last_").removesuffix("_ts"): max(0.0, now - getattr(self, name))
                for name in fields}


class Watchdog:
    """Detects idle versus stalled runtime states without reconnecting on ordinary silence."""

    def __init__(self, stall_after_seconds: float = 30.0, idle_after_seconds: float = 5.0) -> None:
        self.stall_after_seconds = stall_after_seconds
        self.idle_after_seconds = idle_after_seconds
        self._health = HealthRecord()
        self._lock = threading.Lock()
        self._last_state = "healthy"

    @property
    def health(self) -> HealthRecord:
        return self._health

    def mark_progress(self, kind: str, **kwargs) -> HealthRecord:
        with self._lock:
            self._health.note_progress(kind, **kwargs)
            self._last_state = "healthy"
            return self._health

    def expect_progress(self, kind: str = "", timeout: float | None = None) -> None:
        """Declare that the current operation is expected to make progress.

        A connected assistant is normally idle between turns.  The watchdog
        only considers a timeout actionable while an operation has explicitly
        opted into supervision.
        """
        with self._lock:
            self._health.set_expectation(
                True,
                kind=kind,
                timeout=self.stall_after_seconds if timeout is None else timeout,
            )

    def clear_expectation(self) -> None:
        with self._lock:
            self._health.set_expectation(False)

    def mark_exception(self) -> None:
        with self._lock:
            self._health.exception_count += 1
            self._health.last_exception_ts = time.monotonic()

    def mark_reconnect(self) -> None:
        with self._lock:
            self._health.reconnect_count += 1
            self._health.last_reconnect_ts = time.monotonic()

    def update_queue(self, queue_name: str, size: int) -> None:
        with self._lock:
            self._health.queue_sizes[queue_name] = size

    def update_worker(self, name: str, status: str) -> None:
        with self._lock:
            self._health.worker_status[name] = status

    def is_idle(self, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        with self._lock:
            age = now - self._health.last_progress_ts
            return age >= self.idle_after_seconds

    def is_stalled(self, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        with self._lock:
            if not self._health.progress_expected:
                return False
            age = now - self._health.last_progress_ts
            timeout = self._health.expected_timeout or self.stall_after_seconds
            return age >= timeout

    def status(self) -> str:
        if self.is_stalled():
            return "stalled"
        if self.is_idle():
            return "idle"
        return "healthy"

    def snapshot(self) -> dict:
        with self._lock:
            return self._health.snapshot()
