"""Wireless channel with independent random packet loss and fixed delay."""
from __future__ import annotations

import random
from collections.abc import Callable

from simulator.event_scheduler import EventScheduler
from simulator.packet import Packet


class WirelessChannel:
    def __init__(self, scheduler: EventScheduler, loss_probability: float = 0.0,
                 delay_ms: float = 25.0, seed: int = 7) -> None:
        if not 0.0 <= loss_probability <= 1.0:
            raise ValueError("loss_probability must be between 0 and 1")
        if delay_ms < 0:
            raise ValueError("delay_ms cannot be negative")
        self.scheduler = scheduler
        self.loss_probability = loss_probability
        self.delay_ms = delay_ms
        self._rng = random.Random(seed)
        self.sent_count = 0
        self.dropped_count = 0
        self.delivered_count = 0
        self.events: list[str] = []

    def transmit(self, packet: Packet, on_delivery: Callable[[Packet], None]) -> None:
        self.sent_count += 1
        direction = "DATA" if packet.packet_type.value == "DATA" else "ACK"
        if self._rng.random() < self.loss_probability:
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
