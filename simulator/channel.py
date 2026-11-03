"""Wireless channel with random loss or a shared packet-keyed loss trace."""
from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Callable

from simulator.event_scheduler import EventScheduler
from simulator.loss_trace import SharedLossTrace
from simulator.packet import Packet, PacketType


class WirelessChannel:
    def __init__(
        self,
        scheduler: EventScheduler,
        loss_probability: float = 0.0,
        delay_ms: float = 25.0,
        seed: int = 7,
        loss_trace: SharedLossTrace | None = None,
    ) -> None:
        if not 0.0 <= loss_probability <= 1.0:
            raise ValueError("loss_probability must be between 0 and 1")
        if delay_ms < 0:
            raise ValueError("delay_ms cannot be negative")
        if loss_trace is not None and loss_trace.loss_probability != loss_probability:
            raise ValueError("loss_trace probability must match loss_probability")
        self.scheduler = scheduler
        self.loss_probability = loss_probability
        self.delay_ms = delay_ms
        self._rng = random.Random(seed)
        self.loss_trace = loss_trace
        self._attempts: defaultdict[tuple[PacketType, int], int] = defaultdict(int)
        self.sent_count = 0
        self.dropped_count = 0
        self.delivered_count = 0
        self.events: list[str] = []

    def transmit(self, packet: Packet, on_delivery: Callable[[Packet], None]) -> None:
        self.sent_count += 1
        packet_type = packet.packet_type
        direction = packet_type.value
        key = (packet_type, packet.sequence_number)
        self._attempts[key] += 1

        if self.loss_trace is None:
            dropped = self._rng.random() < self.loss_probability
        else:
            dropped = self.loss_trace.should_drop(
                packet_type, packet.sequence_number, self._attempts[key]
            )

        if dropped:
            self.dropped_count += 1
            self.events.append(
                f"{self.scheduler.now_ms:8.2f} ms | {direction} seq={packet.sequence_number} DROPPED"
            )
            return

        self.events.append(
            f"{self.scheduler.now_ms:8.2f} ms | {direction} seq={packet.sequence_number} SENT"
        )

        def deliver() -> None:
            self.delivered_count += 1
            self.events.append(
                f"{self.scheduler.now_ms:8.2f} ms | {direction} seq={packet.sequence_number} DELIVERED"
            )
            on_delivery(packet)

        self.scheduler.schedule(self.delay_ms, deliver)
