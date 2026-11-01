#computer_control.py
import io
import json
import platform
import re
import string
import subprocess
import sys
import os

if platform.system() == "Windows":
    _WIN_HIDE: dict = {"creationflags": subprocess.CREATE_NO_WINDOW}
else:
    _WIN_HIDE: dict = {}
import time
import random
from pathlib import Path


def _enable_windows_dpi_awareness() -> None:
    if platform.system() != "Windows":
        return
    try:
        ctypes = __import__("ctypes")
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            ctypes = __import__("ctypes")
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass


_enable_windows_dpi_awareness()

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE    = 0.05
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

try:
    if platform.system() == "Windows":
        from control.windows_input import click as native_click
        from control.windows_input import drag as native_drag
        from control.windows_input import hotkey as native_hotkey
        from control.windows_input import mouse_down as native_mouse_down
        from control.windows_input import mouse_up as native_mouse_up
        from control.windows_input import move_mouse as native_move
        from control.windows_input import press_key as native_press
        from control.windows_input import scroll as native_scroll
        from control.windows_input import type_text as native_type_text
        from control.windows_input import horizontal_scroll as native_horizontal_scroll
        _NATIVE_INPUT = True
        _NATIVE_INPUT_ERROR = ""
    else:
        _NATIVE_INPUT = False
except Exception as exc:
    _NATIVE_INPUT = False
    _NATIVE_INPUT_ERROR = f"{type(exc).__name__}: {exc}"

_ALLOW_PYAUTOGUI_FALLBACK = os.environ.get(
    "JARVIS_ALLOW_PYAUTOGUI_FALLBACK", ""
).strip().lower() in {"1", "true", "yes", "on"}
_CONTROL_BACKEND = (
    "windows-native" if platform.system() == "Windows" and _NATIVE_INPUT
    else "pyautogui-explicit-fallback" if _ALLOW_PYAUTOGUI_FALLBACK
    else "pyautogui-platform" if platform.system() != "Windows" and _PYAUTOGUI
    else "unavailable"
)


def control_backend_status() -> dict[str, str | bool]:
    return {
        "backend": _CONTROL_BACKEND,
        "native_available": _NATIVE_INPUT,
        "fallback_enabled": _ALLOW_PYAUTOGUI_FALLBACK,
        "error": _NATIVE_INPUT_ERROR,
    }


def _require_control_backend() -> None:
    if _CONTROL_BACKEND == "unavailable":
        detail = _NATIVE_INPUT_ERROR or "native Windows input could not be loaded"
        raise RuntimeError(
            f"Native computer control unavailable: {detail}. "
            "Set JARVIS_ALLOW_PYAUTOGUI_FALLBACK=1 only for deliberate fallback testing."
        )

try:
    import pyperclip
    _PYPERCLIP = True
except ImportError:
    _PYPERCLIP = False

try:
    from control.action_verifier import ActionVerifier
    from control.coordinate_mapper import CoordinateMapper
    from control.screen_monitor import ScreenMonitor
    from control.window_manager import WindowManager
    from control.coordinate_mapper import MonitorInfo
    _ACTION_VERIFIER = ActionVerifier()
    _COORD_MAPPER = CoordinateMapper()
    _SCREEN_MONITOR = ScreenMonitor(refresh_hz=30.0)
    _SCREEN_MONITOR.start()
    _WINDOW_MANAGER = WindowManager()
except Exception:
    _ACTION_VERIFIER = None
    _COORD_MAPPER = None
    _SCREEN_MONITOR = None
    _WINDOW_MANAGER = None


def _capture_screen_verification() -> object | None:
    try:
        import mss
        import mss.tools
        with mss.mss() as sct:
            shot = sct.grab(sct.monitors[0])
            return mss.tools.to_png(shot.rgb, shot.size)
    except ImportError:
        if not _PYAUTOGUI:
            return None
        img = pyautogui.screenshot()
        return img.resize((64, 64)).convert("L").tobytes()
    except Exception:
        return None


if _ACTION_VERIFIER is not None:
    _ACTION_VERIFIER.capture_fn = _capture_screen_verification


def _verify_action(action_name: str, *, timeout_seconds: float = 0.8) -> bool:
    if _ACTION_VERIFIER is None or _ACTION_VERIFIER.capture_fn is None:
        return True
    try:
        return _ACTION_VERIFIER.wait_for_change(action_name, timeout_seconds=timeout_seconds, poll_interval=0.05)
    except Exception:
        return True


def _wait_for_expected_change(
    before: object,
    *,
    capture_fn=None,
    timeout_seconds: float = 1.5,
) -> bool:
    capture = capture_fn or (
        _ACTION_VERIFIER.capture_fn
        if _ACTION_VERIFIER is not None else None
    )
    if before is None or capture is None:
        return False
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        after = capture()
        if after is not None and after != before:
            return True
        time.sleep(0.08)
    return False


def _capture_region_verification(x: int, y: int, size: int = 96) -> object | None:
    try:
        import mss
        import mss.tools
        with mss.mss() as sct:
            half = size // 2
            shot = sct.grab({
                "left": int(x) - half,
                "top": int(y) - half,
                "width": size,
                "height": size,
            })
            return mss.tools.to_png(shot.rgb, shot.size)
    except (ImportError, ValueError, OSError):
        return None

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


_BASE         = _base_dir()
_CONFIG_PATH  = _BASE / "config" / "api_keys.json"
_MEMORY_PATH  = _BASE / "memory" / "long_term.json"

def _load_config() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _platform_os() -> str:
    return {"Windows": "windows", "Darwin": "mac", "Linux": "linux"}.get(
        platform.system(), "linux"
    )

def _get_os() -> str:
    return _load_config().get("os_system", _platform_os()).lower()


def _get_api_key() -> str:
    return _load_config().get("gemini_api_key", "")

_SAFE_SCREENSHOT_ROOTS = (
    Path.home(),
)

def _safe_screenshot_path(requested: str | None) -> Path:
    fallback = Path.home() / "Desktop" / "jarvis_screenshot.png"
    if not requested:
        return fallback
    try:
        p = Path(requested).expanduser().resolve()
        for root in _SAFE_SCREENSHOT_ROOTS:
            if p.is_relative_to(root.resolve()):
                p.parent.mkdir(parents=True, exist_ok=True)
                return p
    except Exception:
        pass
    return fallback

def _require_pyautogui():
    if not _PYAUTOGUI:
        raise RuntimeError("PyAutoGUI not installed. Run: pip install pyautogui")

_FIRST_NAMES = [
    "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Drew", "Quinn",
    "Avery", "Blake", "Cameron", "Dakota", "Emerson", "Finley", "Harper",
]
_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Wilson", "Moore", "Taylor", "Anderson", "Thomas", "Jackson",
]
_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "proton.me", "mail.com"]


def _random_data(data_type: str) -> str:
    dt = data_type.lower().strip()

    if dt == "first_name":
        return random.choice(_FIRST_NAMES)

    if dt == "last_name":
        return random.choice(_LAST_NAMES)

    if dt == "name":
        return f"{random.choice(_FIRST_NAMES)} {random.choice(_LAST_NAMES)}"

    if dt == "email":
        first = random.choice(_FIRST_NAMES).lower()
        last  = random.choice(_LAST_NAMES).lower()
        num   = random.randint(10, 999)
        return f"{first}.{last}{num}@{random.choice(_DOMAINS)}"

    if dt == "username":
        return f"{random.choice(_FIRST_NAMES).lower()}{random.randint(100, 9999)}"

    if dt == "password":
        chars = string.ascii_letters + string.digits + "!@#$%"
        raw   = (
            random.choice(string.ascii_uppercase)
            + random.choice(string.digits)
            + random.choice("!@#$%")
            + "".join(random.choices(chars, k=9))
        )
        return "".join(random.sample(raw, len(raw)))

    if dt == "phone":
        return f"+1{random.randint(200,999)}{random.randint(1_000_000, 9_999_999)}"

    if dt == "birthday":
        y = random.randint(1980, 2000)
        m = random.randint(1, 12)
        d = random.randint(1, 28)
        return f"{m:02d}/{d:02d}/{y}"

    if dt == "address":
        num    = random.randint(100, 9999)
        street = random.choice(["Main St", "Oak Ave", "Park Blvd", "Elm St", "Cedar Ln"])
        return f"{num} {street}"

    if dt == "zip_code":
        return str(random.randint(10000, 99999))

    if dt == "city":
        return random.choice(["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"])

    return f"random_{data_type}_{random.randint(1000, 9999)}"

def _user_profile() -> dict:
    """Read identity fields from long-term memory."""
    try:
        if _MEMORY_PATH.exists():
            data     = json.loads(_MEMORY_PATH.read_text(encoding="utf-8"))
            identity = data.get("identity", {})
            return {k: v.get("value", "") for k, v in identity.items()}
    except Exception:
        pass
    return {}

def _type(text: str, interval: float = 0.03) -> str:
    _require_control_backend()
    if _CONTROL_BACKEND == "windows-native":
        native_type_text(text, interval=interval)
        _verify_action("type")
        return f"Typed: {text[:60]}{'…' if len(text) > 60 else ''}"
    _require_pyautogui()
    time.sleep(0.3)
    pyautogui.typewrite(text, interval=interval)
    _verify_action("type")
    return f"Typed: {text[:60]}{'…' if len(text) > 60 else ''}"


def _smart_type(text: str, clear_first: bool = True) -> str:
    _require_control_backend()
    if _CONTROL_BACKEND == "windows-native":
        if clear_first:
            native_hotkey("ctrl", "a")
            native_press("backspace")
        native_type_text(text, interval=0.04)
        return f"Smart-typed: {text[:60]}{'…' if len(text) > 60 else ''}"
    _require_pyautogui()
    if clear_first:
        _clear_field()
        time.sleep(0.1)

    if len(text) > 20 and _PYPERCLIP:
        pyperclip.copy(text)
        time.sleep(0.1)
        paste_key = "command" if _get_os() == "mac" else "ctrl"
        pyautogui.hotkey(paste_key, "v")
        return f"Smart-typed (clipboard): {text[:60]}{'…' if len(text) > 60 else ''}"

    pyautogui.typewrite(text, interval=0.04)
    return f"Smart-typed: {text[:60]}{'…' if len(text) > 60 else ''}"


def _click(x=None, y=None, button: str = "left", clicks: int = 1) -> str:
    _require_control_backend()
    if x is not None and y is not None:
        x, y = int(float(x)), int(float(y))
        if _COORD_MAPPER is not None:
            desktop = _COORD_MAPPER.virtual_desktop()
            if not (desktop.left <= x < desktop.right and desktop.top <= y < desktop.bottom):
                raise ValueError(f"Click coordinates outside the virtual desktop: ({x}, {y})")
        elif _PYAUTOGUI:
            width, height = pyautogui.size()
            if not (0 <= x < width and 0 <= y < height):
                raise ValueError(f"Click coordinates outside the active screen: ({x}, {y})")
    if _CONTROL_BACKEND == "windows-native":
        if x is not None and y is not None:
            native_click(x, y, button=button, clicks=clicks)
            if _ACTION_VERIFIER is None or not _ACTION_VERIFIER.verify_cursor((x, y)):
                raise RuntimeError(f"Click verification failed at ({x}, {y})")
            return f"{'Double-c' if clicks == 2 else 'C'}licked ({x}, {y}) [{button}]"
        native_click(button=button, clicks=clicks)
        return f"Clicked at current position [{button}]"
    _require_pyautogui()
    if x is not None and y is not None:
        pyautogui.click(x, y, button=button, clicks=clicks)
        _verify_action("click")
        return f"{'Double-c' if clicks == 2 else 'C'}licked ({x}, {y}) [{button}]"
    pyautogui.click(button=button, clicks=clicks)
    _verify_action("click")
    return f"Clicked at current position [{button}]"


def _mouse_button(action: str, button: str = "left") -> str:
    _require_control_backend()
    if _CONTROL_BACKEND == "windows-native":
        (native_mouse_down if action == "down" else native_mouse_up)(button)
    else:
        _require_pyautogui()
        (pyautogui.mouseDown if action == "down" else pyautogui.mouseUp)(button=button)
    return f"Mouse {action}: {button}"


def _hotkey(*keys) -> str:
    _require_control_backend()
    flat_keys = []
    for value in keys:
        if value is None:
            continue
        if isinstance(value, str):
            flat_keys.extend(part.strip() for part in re.split(r"[+\s]+", value) if part.strip())
        else:
            flat_keys.extend(str(v).strip() for v in value if str(v).strip())
    rendered = "+".join(flat_keys)
    if _CONTROL_BACKEND == "windows-native":
        native_hotkey(*flat_keys)
        return f"Hotkey: {rendered}"
    _require_pyautogui()
    pyautogui.hotkey(*flat_keys)
    return f"Hotkey: {rendered}"


def _press(key: str) -> str:
    _require_control_backend()
    if _CONTROL_BACKEND == "windows-native":
        native_press(key)
        return f"Pressed: {key}"
    _require_pyautogui()
    pyautogui.press(key)
    return f"Pressed: {key}"


def _scroll(direction: str = "down", amount: int = 3) -> str:
    _require_control_backend()
    if _CONTROL_BACKEND == "windows-native":
        if direction in ("up", "down"):
            native_scroll(amount if direction == "up" else -amount)
        else:
            native_horizontal_scroll(amount if direction == "right" else -amount)
        return f"Scrolled {direction} ×{amount}"
    _require_pyautogui()
    vertical   = direction in ("up", "down")
    clicks     = amount if direction in ("up", "right") else -amount
    pyautogui.scroll(clicks) if vertical else pyautogui.hscroll(clicks)
    return f"Scrolled {direction} ×{amount}"


def _move(x: int, y: int, duration: float = 0.3) -> str:
    _require_control_backend()
    if _CONTROL_BACKEND == "windows-native":
        native_move(x, y, duration=duration)
        if _ACTION_VERIFIER is None or not _ACTION_VERIFIER.verify_cursor((x, y)):
            raise RuntimeError(f"Cursor verification failed at ({x}, {y})")
        return f"Mouse → ({x}, {y})"
    _require_pyautogui()
    pyautogui.moveTo(x, y, duration=duration)
    _verify_action("move")
    return f"Mouse → ({x}, {y})"


def _drag(x1: int, y1: int, x2: int, y2: int, duration: float = 0.5) -> str:
    _require_control_backend()
    if _CONTROL_BACKEND == "windows-native":
        native_drag(x1, y1, x2, y2, duration=duration)
        if _ACTION_VERIFIER is None or not _ACTION_VERIFIER.verify_cursor((x2, y2)):
            raise RuntimeError(f"Drag verification failed at ({x2}, {y2})")
        return f"Dragged ({x1},{y1}) → ({x2},{y2})"
    _require_pyautogui()
    pyautogui.moveTo(x1, y1, duration=0.2)
    pyautogui.dragTo(x2, y2, duration=duration, button="left")
    _verify_action("drag")
    return f"Dragged ({x1},{y1}) → ({x2},{y2})"


def _clipboard_get() -> str:
    if _PYPERCLIP:
        return pyperclip.paste()
    _hotkey("ctrl", "c")
    time.sleep(0.2)
    return "(copied — pyperclip unavailable for read)"


def _clipboard_paste(text: str) -> str:
    if _PYPERCLIP:
        pyperclip.copy(text)
        time.sleep(0.1)
        _require_pyautogui()
        paste_key = "command" if _get_os() == "mac" else "ctrl"
        pyautogui.hotkey(paste_key, "v")
        return f"Pasted: {text[:60]}{'…' if len(text) > 60 else ''}"
    return "pyperclip not available"


def _screenshot(save_path: str | None = None) -> str:
    _require_pyautogui()
    path = _safe_screenshot_path(save_path)
    img  = pyautogui.screenshot()
    img.save(str(path))
    return f"Screenshot saved: {path}"


def _clear_field() -> str:
    _require_pyautogui()
    select_key = "command" if _get_os() == "mac" else "ctrl"
    pyautogui.hotkey(select_key, "a")
    time.sleep(0.1)
    pyautogui.press("delete")
    return "Field cleared"

def _focus_window(title: str) -> str:
    os_name = _get_os()

    if os_name == "windows":
        try:
            if _WINDOW_MANAGER is None or not _WINDOW_MANAGER.focus_window_by_title(title):
                return f"Focus failed: no visible window matched '{title}'"
            time.sleep(0.3)
            info = _WINDOW_MANAGER.foreground_window()
            if info is None or title.lower() not in info.title.lower():
                return f"Focus failed: '{title}' is not foreground"
            return f"Focused window: {title}"
        except Exception as e:
            return f"focus_window (Windows) failed: {e}"

    if os_name == "mac":
        script = (
            f'tell application "System Events" to '
            f'set frontmost of (first process whose name contains "{title}") to true'
        )
        try:
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, timeout=5,
            )
            time.sleep(0.3)
            return f"Focused window: {title}"
        except Exception as e:
            return f"focus_window (macOS) failed: {e}"

    if os_name == "linux":
        try:
            result = subprocess.run(
                ["wmctrl", "-a", title],
                capture_output=True, timeout=5,
            )
            if result.returncode == 0:
                time.sleep(0.3)
                return f"Focused window: {title}"
        except FileNotFoundError:
            pass
        try:
            result = subprocess.run(
                ["xdotool", "search", "--name", title, "windowactivate"],
                capture_output=True, timeout=5,
            )
            time.sleep(0.3)
            return f"Focused window: {title}"
        except FileNotFoundError:
            return "focus_window (Linux) requires wmctrl or xdotool"
        except Exception as e:
            return f"focus_window (Linux) failed: {e}"

    return f"focus_window: unknown OS '{os_name}'"

def _screen_find(description: str) -> tuple[int, int] | None:
    api_key = _get_api_key()
    if not api_key:
        print("[ComputerControl] ⚠️ No API key for screen_find")
        return None

    try:
        from google import genai
        from google.genai import types as gtypes

        try:
            import mss
            import mss.tools
            snapshot = (
                _SCREEN_MONITOR.fresh(max_age_seconds=0.10)
                if _SCREEN_MONITOR is not None else None
            )
            if snapshot is not None:
                w, h, image_bytes = snapshot.width, snapshot.height, snapshot.image
                image_origin = (snapshot.left, snapshot.top)
            else:
                with mss.mss() as sct:
                    monitor = sct.monitors[0]
                    shot = sct.grab(monitor)
                    w, h = shot.size
                    image_bytes = mss.tools.to_png(shot.rgb, shot.size)
                    image_origin = (int(monitor["left"]), int(monitor["top"]))
        except ImportError:
            _require_pyautogui()
            img = pyautogui.screenshot()
            w, h = img.size
            image_origin = (0, 0)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            image_bytes = buf.getvalue()

        prompt = (
            f"This is a screenshot of a {w}×{h} pixel screen. "
            f"Locate the UI element described as: '{description}'. "
            f"Reply with ONLY the center coordinates as: x,y "
            f"If the element is not visible, reply: NOT_FOUND"
        )

        from core import gemini
        response = gemini.call(
            [gtypes.Part.from_bytes(data=image_bytes, mime_type="image/png"), prompt],
            tier=gemini.FAST, timeout_ms=20_000,
        )
        if response is None:
            return None

        text = (response.text or "").strip()
        if "NOT_FOUND" in text.upper():
            return None

        match = re.search(r"(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)", text)
        if match:
            image_x = float(match.group(1))
            image_y = float(match.group(2))
            if not (0 <= image_x < w and 0 <= image_y < h):
                print(f"[ComputerControl] ⚠️ screen_find returned out-of-bounds coordinates: {text}")
                return None
            if _COORD_MAPPER is not None:
                left, top = image_origin
                return _COORD_MAPPER.vision_to_cursor(
                    image_x,
                    image_y,
                    screenshot_size=(w, h),
                    monitor=MonitorInfo(
                        left=left,
                        top=top,
                        right=left + w,
                        bottom=top + h,
                        width=w,
                        height=h,
                    ),
                )
            return int(image_x), int(image_y)

    except Exception as e:
        print(f"[ComputerControl] ⚠️ screen_find failed: {e}")

    return None


def _build_click_plan(description: str) -> dict:
    """Choose the best control mode: direct hotkey for tab/window commands, screen click for visual UI targets."""
    text = (description or "").lower().strip()
    if not text:
        return {"mode": "screen", "description": "target"}

    direct_commands = {
        "close tab": {"mode": "hotkey", "keys": ("ctrl", "w")},
        "close this tab": {"mode": "hotkey", "keys": ("ctrl", "w")},
        "close window": {"mode": "hotkey", "keys": ("alt", "f4")},
        "close app": {"mode": "hotkey", "keys": ("alt", "f4")},
        "new tab": {"mode": "hotkey", "keys": ("ctrl", "t")},
        "new window": {"mode": "hotkey", "keys": ("ctrl", "n")},
        "refresh": {"mode": "hotkey", "keys": ("f5",)},
        "go back": {"mode": "hotkey", "keys": ("alt", "left")},
        "go forward": {"mode": "hotkey", "keys": ("alt", "right")},
        "open task manager": {"mode": "hotkey", "keys": ("ctrl", "shift", "esc")},
        "show desktop": {"mode": "hotkey", "keys": ("win", "d")},
    }

    for phrase, plan in direct_commands.items():
        if phrase in text:
            return plan

    if any(token in text for token in ("button", "menu", "search", "field", "input", "textbox", "icon", "close", "save", "open", "settings")):
        return {"mode": "screen", "description": text}

    return {"mode": "screen", "description": text}

def computer_control(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Dispatch table for all computer control actions.

    parameters keys (all optional unless noted):
      action        : (required) one of the actions listed below
      text          : text to type or paste
      x, y          : screen coordinates
      button        : 'left' | 'right' (default: left)
      keys          : hotkey string, e.g. 'ctrl+c'
      key           : single key name, e.g. 'enter'
      direction     : 'up' | 'down' | 'left' | 'right'
      amount        : scroll amount (default: 3)
      seconds       : wait duration
      title         : window title fragment for focus_window
      description   : natural-language element description for screen_find/click
      type          : data type for random_data
      field         : memory field name for user_data
      clear_first   : bool, clear field before typing (default: true)
      path          : save path for screenshot (must be inside home dir)

    Actions:
      type          — type text at cursor
      smart_type    — clear field + type (clipboard-backed)
      click         — left click
      double_click  — double left click
      right_click   — right click
      mouse_down    — press and hold a mouse button
      mouse_up      — release a mouse button
      move          — move mouse
      drag          — click-drag between two points
      hotkey        — key combination
      press         — single key
      scroll        — scroll the wheel
      copy          — read clipboard
      paste         — write + paste clipboard
      screenshot    — capture screen (safe path only)
      wait          — sleep N seconds
      clear_field   — select-all + delete
      focus_window  — bring window to foreground
      screen_find   — AI element finder (returns x,y)
      screen_click  — AI element finder + click
      random_data   — generate fake form data
      user_data     — pull real data from memory
    """
    params = parameters or {}
    action = params.get("action", "").lower().strip()

    if not action:
        return "No action specified for computer_control."

    if player:
        player.write_log(f"[Computer] {action}")

    print(f"[ComputerControl] ▶ {action}  {params}")

    try:

        if action == "type":
            return _type(params.get("text", ""))

        if action == "smart_type":
            return _smart_type(
                params.get("text", ""),
                clear_first=params.get("clear_first", True),
            )

        if action in ("click", "left_click"):
            return _click(params.get("x"), params.get("y"), "left", 1)

        if action == "double_click":
            return _click(params.get("x"), params.get("y"), "left", 2)

        if action == "right_click":
            return _click(params.get("x"), params.get("y"), "right", 1)

        if action == "move":
            return _move(
                int(params.get("x", 0)),
                int(params.get("y", 0)),
                duration=max(0.0, float(params.get("duration", 0.0))),
            )

        if action in ("mouse_down", "mouse_up"):
            return _mouse_button(
                "down" if action == "mouse_down" else "up",
                params.get("button", "left"),
            )

        if action == "drag":
            return _drag(
                int(params.get("x1", 0)), int(params.get("y1", 0)),
                int(params.get("x2", 0)), int(params.get("y2", 0)),
            )

        if action == "hotkey":
            raw  = params.get("keys", "")
            keys = [k.strip() for k in raw.split("+")] if isinstance(raw, str) else raw
            return _hotkey(*keys)

        if action == "press":
            return _press(params.get("key", "enter"))

        if action == "scroll":
            return _scroll(
                direction=params.get("direction", "down"),
                amount=int(params.get("amount", 3)),
            )

        if action == "copy":
            return _clipboard_get()

        if action == "paste":
            return _clipboard_paste(params.get("text", ""))

        if action == "screenshot":
            return _screenshot(params.get("path"))

        if action == "screen_find":
            coords = _screen_find(params.get("description", ""))
            return f"{coords[0]},{coords[1]}" if coords else "NOT_FOUND"

        if action == "screen_click":
            desc   = params.get("description", "")
            coords = _screen_find(desc)
            if coords:
                before = _capture_region_verification(*coords)
                _move(coords[0], coords[1], duration=0.15)
                _click(x=coords[0], y=coords[1])
                if before is None or not _wait_for_expected_change(
                    before, capture_fn=lambda: _capture_region_verification(*coords)
                ):
                    return (
                        f"Clicked '{desc}' at {coords}; "
                        "no visible screen change was detected"
                    )
                return f"Clicked '{desc}' at {coords}"
            return f"Element not found on screen: '{desc}'"

        if action == "smart_action":
            desc = params.get("description", "")
            plan = _build_click_plan(desc)
            if plan["mode"] == "hotkey":
                _hotkey(*plan["keys"])
                verb = "close tab" if "close" in desc.lower() and "tab" in desc.lower() else "dynamic desktop action"
                return f"Smart action: {verb} -> hotkey {'+'.join(plan['keys'])}"
            coords = _screen_find(desc)
            if coords:
                before = _capture_region_verification(*coords)
                _move(coords[0], coords[1], duration=0.15)
                _click(x=coords[0], y=coords[1])
                if before is None or not _wait_for_expected_change(
                    before, capture_fn=lambda: _capture_region_verification(*coords)
                ):
                    return (
                        f"Smart action sent: {desc} -> clicked at {coords}; "
                        "no visible screen change was detected"
                    )
                return f"Smart action: {desc} -> clicked at {coords}"
            return f"Smart action failed: {desc}"

        if action == "wait":
            secs = float(params.get("seconds", 1.0))
            secs = min(secs, 30.0)
            time.sleep(secs)
            return f"Waited {secs}s"

        if action == "clear_field":
            return _clear_field()

        if action == "focus_window":
            return _focus_window(params.get("title", ""))

        if action == "random_data":
            dt     = params.get("type", "name")
            result = _random_data(dt)
            print(f"[ComputerControl] 🎲 random {dt} → {result}")
            return result

        if action == "user_data":
            field   = params.get("field", "name")
            profile = _user_profile()
            value   = profile.get(field, "")
            if not value:
                value = _random_data(field)
                print(f"[ComputerControl] ⚠️ No '{field}' in memory, using random: {value}")
            return value

        return f"Unknown action: '{action}'"

    except Exception as e:
        print(f"[ComputerControl] ❌ {action}: {e}")
        return f"computer_control '{action}' failed: {e}"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "computer_control",
    "description": "Direct OS-level computer control: type, click, hotkeys, scroll, move mouse, screenshots, and screen target selection. Use this as the primary tool for direct keyboard and cursor control on the PC. Do not rely on generic app-launch wrappers when the user wants real desktop interaction.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "type | smart_type | click | double_click | right_click | mouse_down | mouse_up | hotkey | press | scroll | move | copy | paste | screenshot | wait | clear_field | focus_window | screen_find | screen_click | random_data | user_data"
            },
            "text": {
                "type": "STRING",
                "description": "Text to type or paste"
            },
            "x": {
                "type": "INTEGER",
                "description": "X coordinate"
            },
            "y": {
                "type": "INTEGER",
                "description": "Y coordinate"
            },
            "keys": {
                "type": "STRING",
                "description": "Key combination e.g. 'ctrl+c'"
            },
            "key": {
                "type": "STRING",
                "description": "Single key e.g. 'enter'"
            },
            "direction": {
                "type": "STRING",
                "description": "up | down | left | right"
            },
            "amount": {
                "type": "INTEGER",
                "description": "Scroll amount (default: 3)"
            },
            "seconds": {
                "type": "NUMBER",
                "description": "Seconds to wait"
            },
            "title": {
                "type": "STRING",
                "description": "Window title for focus_window"
            },
            "description": {
                "type": "STRING",
                "description": "Element description for screen_find/screen_click"
            },
            "type": {
                "type": "STRING",
                "description": "Data type for random_data"
            },
            "field": {
                "type": "STRING",
                "description": "Field for user_data: name|email|city"
            },
            "clear_first": {
                "type": "BOOLEAN",
                "description": "Clear field before typing (default: true)"
            },
            "path": {
                "type": "STRING",
                "description": "Save path for screenshot"
            }
        },
        "required": [
            "action"
        ]
    },
    "handler": computer_control,
}
