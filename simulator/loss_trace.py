"""Deterministic, packet-keyed loss decisions for fair algorithm comparisons."""
from __future__ import annotations

import random

from simulator.packet import PacketType


class SharedLossTrace:
    """Return the same loss outcome for the same direction/sequence/attempt key.

    Separate simulator runs using the same seed and loss probability therefore
    see identical outcomes for corresponding DATA and ACK transmission attempts,
    even if the algorithms transmit packets in a different temporal order.
    """

    def __init__(self, loss_probability: float, seed: int = 7) -> None:
        if not 0.0 <= loss_probability <= 1.0:
            raise ValueError("loss_probability must be between 0 and 1")
        self.loss_probability = loss_probability
        self.seed = seed

    def should_drop(
        self, packet_type: PacketType, sequence_number: int, attempt_number: int
    ) -> bool:
        if sequence_number < 0 or attempt_number < 1:
            raise ValueError("sequence_number must be >= 0 and attempt_number >= 1")
        if self.loss_probability == 0.0:
            return False
        if self.loss_probability == 1.0:
            return True

        # Build a stable integer key; do not use Python's process-randomized hash().
        direction_code = 1 if packet_type is PacketType.DATA else 2
        key = (
            (self.seed & 0xFFFFFFFF) << 64
            | (direction_code & 0xFF) << 56
            | (sequence_number & 0xFFFFFFFF) << 24
            | (attempt_number & 0xFFFFFF)
        )
        return random.Random(key).random() < self.loss_probability
