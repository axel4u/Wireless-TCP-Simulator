"""Shared time-indexed Gilbert-Elliott trace for fair channel comparisons."""
from __future__ import annotations

import hashlib
import random

from simulator.packet import PacketType


class SharedBurstLossTrace:
    """A deterministic channel-state timeline addressed by simulation time.

    Each run with the same seed and parameters sees the same GOOD/BAD state
    at every time slot. Packet loss is sampled from that state's probability
    using a stable key, so a different sender schedule does not advance or
    otherwise perturb the underlying channel timeline.
    """

    GOOD = "GOOD"
    BAD = "BAD"

    def __init__(
        self,
        good_to_bad_probability: float = 0.02,
        bad_to_good_probability: float = 0.25,
        good_state_loss_probability: float = 0.01,
        bad_state_loss_probability: float = 0.80,
        seed: int = 7,
        slot_duration_ms: float = 1.0,
    ) -> None:
        values = {
            "good_to_bad_probability": good_to_bad_probability,
            "bad_to_good_probability": bad_to_good_probability,
            "good_state_loss_probability": good_state_loss_probability,
            "bad_state_loss_probability": bad_state_loss_probability,
        }
        for name, value in values.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        if slot_duration_ms <= 0:
            raise ValueError("slot_duration_ms must be > 0")
        self.good_to_bad_probability = good_to_bad_probability
        self.bad_to_good_probability = bad_to_good_probability
        self.good_state_loss_probability = good_state_loss_probability
        self.bad_state_loss_probability = bad_state_loss_probability
        self.seed = seed
        self.slot_duration_ms = slot_duration_ms
        self._rng = random.Random(seed)
        self._states = [self.GOOD]
        self._attempted_states: list[str] = []
        self.drop_count = 0
        self.attempt_count = 0

    def _ensure_slot(self, slot: int) -> None:
        while len(self._states) <= slot:
            previous = self._states[-1]
            draw = self._rng.random()
            if previous == self.GOOD:
                current = self.BAD if draw < self.good_to_bad_probability else self.GOOD
            else:
                current = self.GOOD if draw < self.bad_to_good_probability else self.BAD
            self._states.append(current)

    def state_at(self, time_ms: float) -> str:
        if time_ms < 0:
            raise ValueError("time_ms must be >= 0")
        slot = int(time_ms // self.slot_duration_ms)
        self._ensure_slot(slot)
        return self._states[slot]

    def should_drop(
        self,
        time_ms: float,
        packet_type: PacketType,
        sequence_number: int,
        attempt_number: int,
    ) -> bool:
        if sequence_number < 0 or attempt_number < 1:
            raise ValueError("sequence_number must be >= 0 and attempt_number >= 1")
        slot = int(time_ms // self.slot_duration_ms)
        state = self.state_at(time_ms)
        self._attempted_states.append(state)
        self.attempt_count += 1
        probability = (
            self.good_state_loss_probability
            if state == self.GOOD else self.bad_state_loss_probability
        )
        direction_code = 1 if packet_type is PacketType.DATA else 2
        key = (
            f"{self.seed}|{slot}|{direction_code}|"
            f"{sequence_number}|{attempt_number}"
        ).encode("utf-8")
        draw = int.from_bytes(hashlib.blake2b(key, digest_size=8).digest(), "big") / 2**64
        dropped = draw < probability
        if dropped:
            self.drop_count += 1
        return dropped

    @property
    def good_state_attempts(self) -> int:
        return self._attempted_states.count(self.GOOD)

    @property
    def bad_state_attempts(self) -> int:
        return self._attempted_states.count(self.BAD)

    @property
    def measured_loss_rate(self) -> float:
        return self.drop_count / self.attempt_count if self.attempt_count else 0.0
