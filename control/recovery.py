from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable


@dataclass
class RecoveryPlan:
    max_retries: int = 3
    backoff_seconds: float = 1.0
    strategy: str = "OBSERVE_AGAIN"
    retry_count: int = 0
    last_error: str = ""
    notes: list[str] = field(default_factory=list)

    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries

    def next_delay(self) -> float:
        return self.backoff_seconds * (2 ** min(self.retry_count, 4))

    def record_retry(self, error: str) -> None:
        self.retry_count += 1
        self.last_error = error
        self.notes.append(error)

    def reset(self) -> None:
        self.retry_count = 0
        self.last_error = ""
        self.notes.clear()


class RecoveryPolicy:
    """Small bounded retry strategy for transient UI and live-session failures."""

    def __init__(self, max_retries: int = 3, backoff_seconds: float = 1.0) -> None:
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds

    def build_plan(self, *, strategy: str = "OBSERVE_AGAIN", notes: Iterable[str] | None = None) -> RecoveryPlan:
        return RecoveryPlan(
            max_retries=self.max_retries,
            backoff_seconds=self.backoff_seconds,
            strategy=strategy,
            notes=list(notes or ()),
        )

    def should_retry(self, plan: RecoveryPlan) -> bool:
        return plan.can_retry()
