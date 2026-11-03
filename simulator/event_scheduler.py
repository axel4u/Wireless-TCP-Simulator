"""Minimal deterministic discrete-event scheduler."""
from __future__ import annotations

import heapq
from collections.abc import Callable
from dataclasses import dataclass, field
from itertools import count


@dataclass(order=True)
class _ScheduledEvent:
    time_ms: float
    order: int
    callback: Callable[[], None] = field(compare=False)


class EventScheduler:
    def __init__(self) -> None:
        self.now_ms = 0.0
        self._queue: list[_ScheduledEvent] = []
        self._counter = count()

    def schedule(self, delay_ms: float, callback: Callable[[], None]) -> None:
        if delay_ms < 0:
            raise ValueError("delay_ms cannot be negative")
        heapq.heappush(self._queue, _ScheduledEvent(
            self.now_ms + delay_ms, next(self._counter), callback
        ))

    def run(self, max_events: int = 1_000_000) -> int:
        """Execute queued events; the event cap protects against runaway loops."""
        if max_events < 1:
            raise ValueError("max_events must be >= 1")
        executed = 0
        while self._queue:
            if executed >= max_events:
                raise RuntimeError("event limit reached; possible runaway event loop")
            event = heapq.heappop(self._queue)
            self.now_ms = event.time_ms
            event.callback()
            executed += 1
        return executed

    @property
    def pending_events(self) -> int:
        return len(self._queue)
