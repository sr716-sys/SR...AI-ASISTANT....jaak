from __future__ import annotations

import platform
import ctypes
from dataclasses import dataclass
from typing import Optional


@dataclass
class MonitorInfo:
    left: int
    top: int
    right: int
    bottom: int
    width: int
    height: int
    dpi_scale: float = 1.0


class SystemMetrics:
    def __init__(self) -> None:
        self.platform = platform.system()
        self.primary_monitor = MonitorInfo(0, 0, 1920, 1080, 1920, 1080, 1.0)
        self._set_dpi_awareness()

    def _set_dpi_awareness(self) -> None:
        if self.platform != "Windows":
            return
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except (AttributeError, OSError):
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except (AttributeError, OSError):
                pass

    def monitor_layout(self) -> list[MonitorInfo]:
        if self.platform != "Windows":
            return [self.primary_monitor]
        try:
            import win32api
            monitors = []
            for mon in win32api.EnumDisplayMonitors():
                rect = win32api.GetMonitorInfo(mon[0])["Monitor"]
                left, top, right, bottom = rect
                width = right - left
                height = bottom - top
                monitors.append(MonitorInfo(left, top, right, bottom, width, height, 1.0))
            return monitors or [self.primary_monitor]
        except (ImportError, OSError):
            try:
                user32 = ctypes.windll.user32
                left = user32.GetSystemMetrics(76)   # SM_XVIRTUALSCREEN
                top = user32.GetSystemMetrics(77)    # SM_YVIRTUALSCREEN
                width = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
                height = user32.GetSystemMetrics(79) # SM_CYVIRTUALSCREEN
                return [MonitorInfo(left, top, left + width, top + height, width, height, 1.0)]
            except (AttributeError, OSError):
                return [self.primary_monitor]


class CoordinateMapper:
    """Convert from vision/image coordinates to physical Windows desktop coordinates."""

    def __init__(self, screenshot_size: tuple[int, int] | None = None, desktop_size: tuple[int, int] | None = None) -> None:
        self.system = SystemMetrics()
        virtual = self.virtual_desktop()
        self.screenshot_size = screenshot_size or (virtual.width, virtual.height)
        self.desktop_size = desktop_size or (virtual.width, virtual.height)

    def virtual_desktop(self) -> MonitorInfo:
        monitors = self.system.monitor_layout()
        left = min(m.left for m in monitors)
        top = min(m.top for m in monitors)
        right = max(m.right for m in monitors)
        bottom = max(m.bottom for m in monitors)
        return MonitorInfo(left, top, right, bottom, right - left, bottom - top, 1.0)

    def image_to_desktop(self, x: float, y: float, *, screenshot_size: tuple[int, int] | None = None, monitor: Optional[MonitorInfo] = None) -> tuple[int, int]:
        img_w, img_h = screenshot_size or self.screenshot_size
        if img_w <= 0 or img_h <= 0:
            return (int(x), int(y))
        # Screenshot coordinates are pixels in the captured image.  Win32
        # monitor rectangles are already physical desktop coordinates, so DPI
        # is represented by their physical width/height rather than applied a
        # second time (which would double-scale high-DPI displays).
        target = monitor or self.virtual_desktop()
        target_w = target.width if target is not None else self.desktop_size[0]
        target_h = target.height if target is not None else self.desktop_size[1]
        scale_x = target_w / img_w
        scale_y = target_h / img_h
        px = target.left + (x * scale_x)
        py = target.top + (y * scale_y)
        return (int(px), int(py))

    def image_to_screen(self, x: float, y: float, **kwargs) -> tuple[int, int]:
        return self.image_to_desktop(x, y, **kwargs)

    def vision_to_cursor(self, x: float, y: float, *, screenshot_size: tuple[int, int] | None = None, monitor: Optional[MonitorInfo] = None) -> tuple[int, int]:
        return self.image_to_desktop(x, y, screenshot_size=screenshot_size, monitor=monitor)

    def diagnostics(self, x: float, y: float, *, monitor: Optional[MonitorInfo] = None) -> dict:
        desktop_x, desktop_y = self.vision_to_cursor(x, y, monitor=monitor)
        return {
            "vision": (x, y),
            "desktop": (desktop_x, desktop_y),
            "monitor": monitor,
            "screenshot_size": self.screenshot_size,
            "desktop_size": self.desktop_size,
        }


__all__ = ["MonitorInfo", "SystemMetrics", "CoordinateMapper"]
