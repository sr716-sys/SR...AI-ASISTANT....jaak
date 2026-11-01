from __future__ import annotations

import time
import platform
import ctypes
from typing import Callable, Optional


class ActionVerifier:
    """Simple verification hooks used after UI actions."""

    def __init__(self, capture_fn: Optional[Callable[[], object]] = None) -> None:
        self.capture_fn = capture_fn

    def before_after(self, action_name: str, before: Optional[object] = None, after: Optional[object] = None) -> bool:
        if before is None or after is None:
            return False
        return before != after

    @staticmethod
    def cursor_position() -> tuple[int, int] | None:
        if platform.system() != "Windows":
            return None
        class _POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
        value = _POINT()
        if not ctypes.windll.user32.GetCursorPos(ctypes.byref(value)):
            return None
        return value.x, value.y

    def verify_cursor(self, expected: tuple[int, int]) -> bool:
        return self.cursor_position() == (int(expected[0]), int(expected[1]))

    def verify_foreground(self, *, title: str | None = None, pid: int | None = None) -> bool:
        if platform.system() != "Windows":
            return False
        try:
            import win32gui
            import win32process
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return False
            if title and title.lower() not in win32gui.GetWindowText(hwnd).lower():
                return False
            if pid is not None and win32process.GetWindowThreadProcessId(hwnd)[1] != pid:
                return False
            return True
        except (ImportError, OSError):
            return False

    def wait_for_change(self, action_name: str, timeout_seconds: float = 1.5, poll_interval: float = 0.1) -> bool:
        if self.capture_fn is None:
            return True
        before = self.capture_fn()
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            after = self.capture_fn()
            if before != after:
                return True
            time.sleep(poll_interval)
        return False


__all__ = ["ActionVerifier"]
