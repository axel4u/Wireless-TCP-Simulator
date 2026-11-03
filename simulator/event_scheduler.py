"""Deterministic discrete-event scheduler with cancellable events."""
from __future__ import annotations

import heapq
from collections.abc import Callable
from dataclasses import dataclass, field
from itertools import count


@dataclass(order=True)
class _ScheduledEvent:
    time_ms: float
    order: int
    event_id: int = field(compare=False)
    callback: Callable[[], None] = field(compare=False)


class EventScheduler:
    def __init__(self) -> None:
        self.now_ms = 0.0
        self._queue: list[_ScheduledEvent] = []
        self._counter = count()
        self._cancelled: set[int] = set()

    def schedule(self, delay_ms: float, callback: Callable[[], None]) -> int:
        if delay_ms < 0:
            raise ValueError("delay_ms cannot be negative")
        event_id = next(self._counter)
        heapq.heappush(self._queue, _ScheduledEvent(
            self.now_ms + delay_ms, event_id, event_id, callback
        ))
        return event_id

    def cancel(self, event_id: int) -> None:
        """Cancel a pending event. Cancelling an already-run event is harmless."""
        self._cancelled.add(event_id)

    def run(self, max_events: int = 1_000_000) -> int:
        """Execute queued events; the event cap protects against runaway loops."""
        if max_events < 1:
            raise ValueError("max_events must be >= 1")
        executed = 0
        while self._queue:
            event = heapq.heappop(self._queue)
            if event.event_id in self._cancelled:
                self._cancelled.remove(event.event_id)
                continue
            if executed >= max_events:
                raise RuntimeError("event limit reached; possible runaway event loop")
            self.now_ms = event.time_ms
            event.callback()
            executed += 1
        return executed

    @property
    def pending_events(self) -> int:
        return sum(event.event_id not in self._cancelled for event in self._queue)
