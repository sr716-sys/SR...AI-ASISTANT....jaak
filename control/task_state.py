from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Optional


class TaskState(str, Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    UNDERSTANDING = "UNDERSTANDING"
    PLANNING = "PLANNING"
    OBSERVING = "OBSERVING"
    ACTING = "ACTING"
    VERIFYING = "VERIFYING"
    RECOVERING = "RECOVERING"
    CONTINUING = "CONTINUING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class TaskProgress:
    task_id: str
    state: TaskState = TaskState.IDLE
    last_transition: float = field(default_factory=time.monotonic)
    progress_note: str = "initialized"
    last_progress_ts: float = field(default_factory=time.monotonic)
    retries: int = 0
    cancelled: bool = False


class TaskStateMachine:
    """Small explicit state tracker for long-running tasks."""

    def __init__(self, task_id: str = "default"):
        self.task_id = task_id
        self.task = TaskProgress(task_id=task_id)

    def transition(self, new_state: TaskState | str, note: str = "") -> TaskProgress:
        state = new_state if isinstance(new_state, TaskState) else TaskState(str(new_state).upper())
        now = time.monotonic()
        self.task.state = state
        self.task.last_transition = now
        self.task.last_progress_ts = now
        if note:
            self.task.progress_note = note
        return self.task

    def mark_progress(self, note: str = "") -> TaskProgress:
        now = time.monotonic()
        self.task.last_progress_ts = now
        if note:
            self.task.progress_note = note
        return self.task

    def cancel(self, note: str = "cancelled") -> TaskProgress:
        self.task.cancelled = True
        self.task.state = TaskState.CANCELLED
        self.task.last_transition = time.monotonic()
        self.task.last_progress_ts = time.monotonic()
        if note:
            self.task.progress_note = note
        return self.task

    def is_stale(self, age_seconds: float) -> bool:
        return (time.monotonic() - self.task.last_progress_ts) > age_seconds

    def snapshot(self) -> dict:
        return {
            "task_id": self.task.task_id,
            "state": self.task.state.value,
            "last_transition": self.task.last_transition,
            "last_progress_ts": self.task.last_progress_ts,
            "progress_note": self.task.progress_note,
            "cancelled": self.task.cancelled,
            "retries": self.task.retries,
        }
