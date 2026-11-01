from __future__ import annotations

from typing import Any

try:
    from actions.open_app import open_app as open_app_tool
except Exception:  # pragma: no cover
    open_app_tool = None

try:
    from actions.computer_control import computer_control
except Exception:  # pragma: no cover
    computer_control = None


def build_capcut_tiktok_pipeline(task: str | None = None) -> list[dict[str, Any]]:
    """Build a deterministic CapCut editing pipeline for a TikTok-style edit.

    The goal is not to guess a random UI workflow but to codify a repeatable,
    observable sequence of actions: open app, focus window, import media,
    select first clip, land on timeline, apply quick massaging edits, then export.
    """
    text = (task or "").lower()
    use_aggressive = "aggressive" in text or "tiktok" in text or "viral" in text

    steps: list[dict[str, Any]] = [
        {"tool": "open_app", "params": {"app_name": "CapCut"}},
        {"tool": "focus_window", "params": {"title": "CapCut"}},
        {"tool": "wait", "params": {"seconds": 2.0}},
        {"tool": "screen_find", "params": {"description": "CapCut import button or media import button"}},
        {"tool": "screen_click", "params": {"description": "CapCut import button or media import button"}},
        {"tool": "wait", "params": {"seconds": 1.5}},
        {"tool": "screen_find", "params": {"description": "first video thumbnail in the import dialog"}},
        {"tool": "screen_click", "params": {"description": "first video thumbnail in the import dialog"}},
        {"tool": "wait", "params": {"seconds": 2.0}},
        {"tool": "screen_find", "params": {"description": "timeline edit area or video track"}},
        {"tool": "screen_click", "params": {"description": "timeline edit area or video track"}},
    ]

    if use_aggressive:
        steps.extend(
            [
                {"tool": "screen_find", "params": {"description": "speed or playback speed control"}},
                {"tool": "screen_click", "params": {"description": "speed or playback speed control"}},
                {"tool": "screen_find", "params": {"description": "fast or 2x speed option"}},
                {"tool": "screen_click", "params": {"description": "fast or 2x speed option"}},
                {"tool": "screen_find", "params": {"description": "cut or split tool"}},
                {"tool": "screen_click", "params": {"description": "cut or split tool"}},
                {"tool": "screen_find", "params": {"description": "text or caption tool"}},
                {"tool": "screen_click", "params": {"description": "text or caption tool"}},
                {"tool": "screen_find", "params": {"description": "export or share button"}},
                {"tool": "screen_click", "params": {"description": "export or share button"}},
            ]
        )
    else:
        steps.extend(
            [
                {"tool": "screen_find", "params": {"description": "export or share button"}},
                {"tool": "screen_click", "params": {"description": "export or share button"}},
            ]
        )

    return steps


def _execute_step(step: dict[str, Any]) -> str:
    tool_name = str(step.get("tool", "")).strip().lower()
    params = step.get("params", {}) or {}

    if tool_name == "open_app":
        if open_app_tool is None:
            return "open_app tool unavailable"
        return open_app_tool({"app_name": params.get("app_name", "CapCut")})

    if tool_name == "focus_window":
        if computer_control is None:
            return "computer_control tool unavailable"
        return computer_control({"action": "focus_window", "title": params.get("title", "CapCut")})

    if tool_name in {"wait"}:
        if computer_control is None:
            return "computer_control tool unavailable"
        return computer_control({"action": "wait", "seconds": float(params.get("seconds", 1.0))})

    if tool_name == "screen_find":
        if computer_control is None:
            return "computer_control tool unavailable"
        res = computer_control({"action": "screen_find", "description": params.get("description", "")})
        return str(res)

    if tool_name == "screen_click":
        if computer_control is None:
            return "computer_control tool unavailable"
        res = computer_control({"action": "screen_click", "description": params.get("description", "")})
        return str(res)

    if tool_name == "hotkey":
        if computer_control is None:
            return "computer_control tool unavailable"
        return computer_control({"action": "hotkey", "keys": params.get("keys", "")})

    return f"Unknown step: {tool_name}"


def execute_capcut_pipeline(task: str | None = None) -> str:
    """Execute the CapCut/TikTok-style workflow in a deterministic, auditable order."""
    steps = build_capcut_tiktok_pipeline(task)
    results: list[str] = []
    for index, step in enumerate(steps, start=1):
        result = _execute_step(step)
        results.append(f"{index}. {step['tool']}: {result}")

    summary = "\n".join(results)
    return f"CapCut pipeline completed for '{task or 'TikTok edit'}'.\n{summary}"


TOOL = {
    "name": "capcut_pipeline",
    "description": "Runs a structured CapCut/TikTok-style editing workflow using window focus, screen detection, and desktop automation.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "task": {
                "type": "STRING",
                "description": "High-level request like 'aggressive TikTok edit' or 'open CapCut and edit the first project'",
            }
        },
        "required": ["task"],
    },
    "handler": lambda parameters=None, response=None, player=None, session_memory=None: execute_capcut_pipeline((parameters or {}).get("task", "")),
}
