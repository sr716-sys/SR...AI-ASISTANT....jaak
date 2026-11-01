from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ScreenSnapshot:
    image: bytes
    width: int
    height: int
    left: int
    top: int
    captured_at: float


class ScreenMonitor:
    """Continuously keeps one recent full-desktop snapshot for visual actions."""

    def __init__(self, refresh_hz: float = 30.0) -> None:
        self._period = 1.0 / max(1.0, float(refresh_hz))
        self._condition = threading.Condition()
        self._snapshot: Optional[ScreenSnapshot] = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._capture_loop, name="screen-monitor", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread, self._thread = self._thread, None
        if thread and thread.is_alive():
            thread.join(timeout=1.0)

    def latest(self, max_age_seconds: float = 0.25) -> ScreenSnapshot | None:
        with self._condition:
            snapshot = self._snapshot
        if snapshot is None or time.monotonic() - snapshot.captured_at > max_age_seconds:
            return None
        return snapshot

    def fresh(self, max_age_seconds: float = 0.10) -> ScreenSnapshot | None:
        """Return a frame only while the monitor layout remains current."""
        return self.latest(max_age_seconds=max_age_seconds)

    def _capture_loop(self) -> None:
        try:
            import mss
            import mss.tools
        except ImportError:
            return

        with mss.mss() as sct:
            while not self._stop.is_set():
                try:
                    monitor = sct.monitors[0]
                    shot = sct.grab(monitor)
                    snapshot = ScreenSnapshot(
                        image=mss.tools.to_png(shot.rgb, shot.size),
                        width=shot.width,
                        height=shot.height,
                        left=int(monitor["left"]),
                        top=int(monitor["top"]),
                        captured_at=time.monotonic(),
                    )
                    with self._condition:
                        self._snapshot = snapshot
                        self._condition.notify_all()
                except Exception:
                    pass
                self._stop.wait(self._period)


__all__ = ["ScreenMonitor", "ScreenSnapshot"]
