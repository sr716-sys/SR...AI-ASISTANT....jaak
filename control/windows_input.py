from __future__ import annotations

import ctypes
import platform
import re
import time
from typing import Iterable


_IS_WINDOWS = platform.system() == "Windows"


def _require_windows() -> None:
    if not _IS_WINDOWS:
        raise RuntimeError("Windows native input is only supported on Windows")


PUL = ctypes.POINTER(ctypes.c_ulong)


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_ushort),
        ("wParamH", ctypes.c_ushort),
    ]


class _InputUnion(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("union", _InputUnion),
    ]


MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x01000

KEYEVENTF_KEYDOWN = 0x0000
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

VK_CODES = {
    "shift": 0x10,
    "ctrl": 0x11,
    "control": 0x11,
    "alt": 0x12,
    "menu": 0x12,
    "win": 0x5B,
    "super": 0x5B,
    "enter": 0x0D,
    "return": 0x0D,
    "escape": 0x1B,
    "esc": 0x1B,
    "tab": 0x09,
    "space": 0x20,
    "backspace": 0x08,
    "delete": 0x2E,
    "del": 0x2E,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    "f1": 0x70,
    "f2": 0x71,
    "f3": 0x72,
    "f4": 0x73,
    "f5": 0x74,
    "f6": 0x75,
    "f7": 0x76,
    "f8": 0x77,
    "f9": 0x78,
    "f10": 0x79,
    "f11": 0x7A,
    "f12": 0x7B,
    "a": 0x41,
    "b": 0x42,
    "c": 0x43,
    "d": 0x44,
    "e": 0x45,
    "f": 0x46,
    "g": 0x47,
    "h": 0x48,
    "i": 0x49,
    "j": 0x4A,
    "k": 0x4B,
    "l": 0x4C,
    "m": 0x4D,
    "n": 0x4E,
    "o": 0x4F,
    "p": 0x50,
    "q": 0x51,
    "r": 0x52,
    "s": 0x53,
    "t": 0x54,
    "u": 0x55,
    "v": 0x56,
    "w": 0x57,
    "x": 0x58,
    "y": 0x59,
    "z": 0x5A,
    "0": 0x30,
    "1": 0x31,
    "2": 0x32,
    "3": 0x33,
    "4": 0x34,
    "5": 0x35,
    "6": 0x36,
    "7": 0x37,
    "8": 0x38,
    "9": 0x39,
    "backquote": 0xC0, "grave": 0xC0,
    "minus": 0xBD, "equals": 0xBB,
    "leftbracket": 0xDB, "rightbracket": 0xDD,
    "backslash": 0xDC, "semicolon": 0xBA,
    "apostrophe": 0xDE, "comma": 0xBC,
    "period": 0xBE, "slash": 0xBF,
    "capslock": 0x14, "insert": 0x2D,
    "printscreen": 0x2C, "pause": 0x13,
    "apps": 0x5D, "numlock": 0x90,
    "volumemute": 0xAD, "volumedown": 0xAE, "volumeup": 0xAF,
}

_SHIFTED_CHARS = {
    "~": "backquote", "!": "1", "@": "2", "#": "3", "$": "4",
    "%": "5", "^": "6", "&": "7", "*": "8", "(": "9", ")": "0",
    "_": "minus", "+": "equals", "{": "leftbracket", "}": "rightbracket",
    "|": "backslash", ":": "semicolon", '"': "apostrophe", "<": "comma",
    ">": "period", "?": "slash",
}
_CHAR_KEYS = {
    "-": "minus", "=": "equals", "[": "leftbracket", "]": "rightbracket",
    "\\": "backslash", ";": "semicolon", "'": "apostrophe", ",": "comma",
    ".": "period", "/": "slash", "`": "backquote",
}


def _resolve_vk(key: str) -> int:
    name = (key or "").lower().strip()
    if name in VK_CODES:
        return VK_CODES[name]
    if name in _CHAR_KEYS:
        return VK_CODES[_CHAR_KEYS[name]]
    raise ValueError(f"Unsupported Windows key: {key!r}")


def _send_input(events: Iterable[INPUT]) -> None:
    _require_windows()
    event_list = list(events)
    if not event_list:
        return
    arr = (INPUT * len(event_list))()
    for i, ev in enumerate(event_list):
        arr[i] = ev
    sent = ctypes.windll.user32.SendInput(len(arr), ctypes.byref(arr), ctypes.sizeof(INPUT))
    if sent != len(arr):
        raise ctypes.WinError()


def _mouse_event(flags: int, dx: int = 0, dy: int = 0, data: int = 0) -> INPUT:
    mi = MOUSEINPUT(dx, dy, data, flags, 0, None)
    ev = INPUT(0, _InputUnion())
    ev.union.mi = mi
    return ev


def _keyboard_event(vk: int, flags: int) -> INPUT:
    ki = KEYBDINPUT(vk, 0, flags, 0, None)
    ev = INPUT(1, _InputUnion())
    ev.union.ki = ki
    return ev


def move_mouse(x: int, y: int, duration: float = 0.1) -> None:
    """Move mouse to absolute desktop coordinates."""
    _require_windows()
    target = (int(x), int(y))
    for attempt in range(6):
        if not ctypes.windll.user32.SetCursorPos(*target):
            raise ctypes.WinError()
        if duration > 0:
            time.sleep(min(duration, 0.25))
        point = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
        if (point.x, point.y) == target:
            return
        time.sleep(0.02)
    raise RuntimeError(f"Windows cursor did not reach {target}; got {(point.x, point.y)}")


def click(x: int | None = None, y: int | None = None, button: str = "left", clicks: int = 1) -> None:
    count = int(clicks)
    if count < 1:
        raise ValueError(f"Click count must be positive: {clicks!r}")
    if x is not None and y is not None:
        move_mouse(x, y, duration=0)
    if button.lower() == "right":
        down, up = MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
    elif button.lower() == "middle":
        down, up = MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP
    elif button.lower() == "left":
        down, up = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP
    else:
        raise ValueError(f"Unsupported mouse button: {button!r}")
    _send_input([
        event
        for _ in range(count)
        for event in (_mouse_event(down), _mouse_event(up))
    ])


def mouse_down(button: str = "left") -> None:
    if button.lower() == "right":
        _send_input([_mouse_event(MOUSEEVENTF_RIGHTDOWN)])
    elif button.lower() == "middle":
        _send_input([_mouse_event(MOUSEEVENTF_MIDDLEDOWN)])
    elif button.lower() == "left":
        _send_input([_mouse_event(MOUSEEVENTF_LEFTDOWN)])
    else:
        raise ValueError(f"Unsupported mouse button: {button!r}")


def mouse_up(button: str = "left") -> None:
    if button.lower() == "right":
        _send_input([_mouse_event(MOUSEEVENTF_RIGHTUP)])
    elif button.lower() == "middle":
        _send_input([_mouse_event(MOUSEEVENTF_MIDDLEUP)])
    elif button.lower() == "left":
        _send_input([_mouse_event(MOUSEEVENTF_LEFTUP)])
    else:
        raise ValueError(f"Unsupported mouse button: {button!r}")


def drag(x1: int, y1: int, x2: int, y2: int, duration: float = 0.2) -> None:
    move_mouse(x1, y1, duration=0.05)
    mouse_down("left")
    time.sleep(max(0.02, min(duration, 0.25)))
    move_mouse(x2, y2, duration=0.05)
    mouse_up("left")


def scroll(amount: int = 3) -> None:
    _send_input([_mouse_event(MOUSEEVENTF_WHEEL, data=int(amount * 120))])


def horizontal_scroll(amount: int = 3) -> None:
    _send_input([_mouse_event(MOUSEEVENTF_HWHEEL, data=int(amount * 120))])


def press_key(key: str) -> None:
    vk = _resolve_vk(key)
    _send_input([_keyboard_event(vk, KEYEVENTF_KEYDOWN), _keyboard_event(vk, KEYEVENTF_KEYUP)])


def key_down(key: str) -> None:
    vk = _resolve_vk(key)
    _send_input([_keyboard_event(vk, KEYEVENTF_KEYDOWN)])


def key_up(key: str) -> None:
    vk = _resolve_vk(key)
    _send_input([_keyboard_event(vk, KEYEVENTF_KEYUP)])


def _unicode_key(char: str) -> None:
    """Send one character through Windows' layout-independent Unicode path."""
    scan = ord(char)
    down = KEYBDINPUT(0, scan, KEYEVENTF_UNICODE, 0, None)
    up = KEYBDINPUT(0, scan, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, None)
    down_event = INPUT(1, _InputUnion())
    up_event = INPUT(1, _InputUnion())
    down_event.union.ki = down
    up_event.union.ki = up
    _send_input([down_event, up_event])


def normalize_key_sequence(*keys: str | Iterable[str]) -> list[str]:
    """Normalize key tokens such as 'alt+tab', 'ctrl + shift + esc', or ('alt', 'tab')."""
    parts: list[str] = []
    for item in keys:
        if item is None:
            continue
        if isinstance(item, str):
            for chunk in re.split(r"[+\s]+", item.strip()):
                token = chunk.strip()
                if token:
                    parts.append(token.lower())
        else:
            for chunk in item:
                token = str(chunk).strip()
                if token:
                    parts.extend(normalize_key_sequence(token))
    return parts


def hotkey(*keys: str | Iterable[str]) -> None:
    normalized = normalize_key_sequence(*keys)
    if not normalized:
        return
    for key in normalized[:-1]:
        key_down(key)
    key_down(normalized[-1])
    for key in reversed(normalized):
        key_up(key)


def type_text(text: str, interval: float = 0.02) -> None:
    if not text:
        return
    for char in text:
        if char == "\n":
            press_key("enter")
        elif char == "\t":
            press_key("tab")
        elif char != "\r":
            # Unicode input preserves case and punctuation independently of the
            # active keyboard layout and avoids modifier-state races.
            _unicode_key(char)
        if interval > 0:
            time.sleep(interval)


__all__ = [
    "move_mouse",
    "click",
    "mouse_down",
    "mouse_up",
    "drag",
    "scroll",
    "horizontal_scroll",
    "press_key",
    "key_down",
    "key_up",
    "hotkey",
    "type_text",
]
