"""Wireless channel with random loss or a shared packet-keyed loss trace."""
from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Callable

from simulator.event_scheduler import EventScheduler
from simulator.loss_trace import SharedLossTrace
from simulator.burst_loss import GilbertElliottLoss
from simulator.shared_burst_trace import SharedBurstLossTrace
from simulator.packet import Packet, PacketType


class WirelessChannel:
    def __init__(
        self,
        scheduler: EventScheduler,
        loss_probability: float = 0.0,
        delay_ms: float = 25.0,
        seed: int = 7,
        loss_trace: SharedLossTrace | None = None,
        burst_loss_model: GilbertElliottLoss | None = None,
        shared_burst_trace: SharedBurstLossTrace | None = None,
    ) -> None:
        if not 0.0 <= loss_probability <= 1.0:
            raise ValueError("loss_probability must be between 0 and 1")
        if delay_ms < 0:
            raise ValueError("delay_ms cannot be negative")
        active_models = sum(model is not None for model in (loss_trace, burst_loss_model, shared_burst_trace))
        if active_models > 1:
            raise ValueError("choose only one loss model or trace")
        if loss_trace is not None and loss_trace.loss_probability != loss_probability:
            raise ValueError("loss_trace probability must match loss_probability")
        self.scheduler = scheduler
        self.loss_probability = loss_probability
        self.delay_ms = delay_ms
        self._rng = random.Random(seed)
        self.loss_trace = loss_trace
        self.burst_loss_model = burst_loss_model
        self.shared_burst_trace = shared_burst_trace
        self._attempts: defaultdict[tuple[PacketType, int], int] = defaultdict(int)
        self.sent_count = 0
        self.dropped_count = 0
        self.delivered_count = 0
        self.events: list[str] = []
        self.transmission_records: list[dict[str, object]] = []

    def transmit(self, packet: Packet, on_delivery: Callable[[Packet], None]) -> None:
        self.sent_count += 1
        packet_type = packet.packet_type
        direction = packet_type.value
        key = (packet_type, packet.sequence_number)
        self._attempts[key] += 1

        channel_state = None
        if self.shared_burst_trace is not None:
            channel_state = self.shared_burst_trace.state_at(self.scheduler.now_ms)
            dropped = self.shared_burst_trace.should_drop(
                self.scheduler.now_ms, packet_type, packet.sequence_number, self._attempts[key]
            )
        elif self.burst_loss_model is not None:
            dropped = self.burst_loss_model.should_drop()
            channel_state = self.burst_loss_model.state
        elif self.loss_trace is None:
            dropped = self._rng.random() < self.loss_probability
        else:
            dropped = self.loss_trace.should_drop(
                packet_type, packet.sequence_number, self._attempts[key]
            )

        self.transmission_records.append({
            "time_ms": self.scheduler.now_ms,
            "packet_type": direction,
            "sequence_number": packet.sequence_number,
            "attempt_number": self._attempts[key],
            "channel_state": channel_state,
            "dropped": dropped,
        })

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
