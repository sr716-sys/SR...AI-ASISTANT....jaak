from __future__ import annotations

import ctypes
import platform
from dataclasses import dataclass
from typing import Optional


@dataclass
class WindowInfo:
    title: str
    process_id: int
    process_name: str
    bounds: tuple[int, int, int, int]
    is_foreground: bool


class WindowManager:
    """Minimal cross-platform window metadata and focus utilities."""

    def __init__(self) -> None:
        self._platform = platform.system()

    def foreground_window(self) -> Optional[WindowInfo]:
        if self._platform != "Windows":
            return None
        try:
            import win32gui
            import win32process
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None
            title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = None
            try:
                proc = win32gui.GetWindowModuleFileName(hwnd)
            except Exception:
                pass
            rect = win32gui.GetWindowRect(hwnd)
            return WindowInfo(
                title=title,
                process_id=pid,
                process_name=(proc or "unknown").split("\\")[-1],
                bounds=(rect[0], rect[1], rect[2], rect[3]),
                is_foreground=True,
            )
        except Exception:
            return None

    def focus_window_by_title(self, title: str) -> bool:
        if self._platform != "Windows":
            return False
        try:
            import win32gui
            needle = (title or "").strip().lower()
            if not needle:
                return False
            candidates = []
            def _enum(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    window_title = win32gui.GetWindowText(hwnd)
                    if needle in window_title.lower():
                        candidates.append(hwnd)
            win32gui.EnumWindows(_enum, None)
            if candidates:
                hwnd = candidates[0]
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, 9)  # SW_RESTORE
                win32gui.SetForegroundWindow(hwnd)
                if win32gui.GetForegroundWindow() != hwnd:
                    import ctypes
                    import win32process
                    foreground = win32gui.GetForegroundWindow()
                    foreground_tid = (
                        win32process.GetWindowThreadProcessId(foreground)[0]
                        if foreground else 0
                    )
                    current_tid = ctypes.windll.kernel32.GetCurrentThreadId()
                    if foreground_tid and foreground_tid != current_tid:
                        ctypes.windll.user32.AttachThreadInput(
                            foreground_tid, current_tid, True
                        )
                    try:
                        win32gui.BringWindowToTop(hwnd)
                        win32gui.SetForegroundWindow(hwnd)
                        win32gui.SetActiveWindow(hwnd)
                    finally:
                        if foreground_tid and foreground_tid != current_tid:
                            ctypes.windll.user32.AttachThreadInput(
                                foreground_tid, current_tid, False
                            )
                return bool(win32gui.GetForegroundWindow() == hwnd)
        except Exception:
            pass
        return False

    def focus_window_by_pid(self, process_id: int) -> bool:
        if self._platform != "Windows":
            return False
        try:
            import win32gui
            import win32process
            candidates = []
            def _enum(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if pid == process_id:
                        candidates.append(hwnd)
            win32gui.EnumWindows(_enum, None)
            for hwnd in candidates:
                win32gui.SetForegroundWindow(hwnd)
                return True
        except Exception:
            pass
        return False

    def ensure_foreground(self, expected_title: str | None = None, expected_pid: int | None = None) -> bool:
        info = self.foreground_window()
        if expected_title and info and info.title and expected_title.lower() in info.title.lower():
            return True
        if expected_pid is not None and info and info.process_id == expected_pid:
            return True
        if expected_title:
            return self.focus_window_by_title(expected_title)
        if expected_pid is not None:
            return self.focus_window_by_pid(expected_pid)
        return False


__all__ = ["WindowInfo", "WindowManager"]
