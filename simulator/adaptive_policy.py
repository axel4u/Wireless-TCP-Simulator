"""Rule-based classification of observable link conditions for adaptive recovery.

The policy never receives the channel's hidden random drop decision or the
actual cause of an individual lost packet.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LinkMetrics:
    """Observable or simulated link measurements supplied to the sender."""

    signal_strength_dbm: float = -65.0
    queue_delay_ms: float = 0.0
    link_retransmissions: int = 0

    def __post_init__(self) -> None:
        if self.queue_delay_ms < 0:
            raise ValueError("queue_delay_ms cannot be negative")
        if self.link_retransmissions < 0:
            raise ValueError("link_retransmissions cannot be negative")


class AdaptiveRecoveryPolicy:
    """Conservative rule-based decision engine for timeout recovery."""

    CONGESTION = "likely_congestion"
    WIRELESS = "likely_wireless"
    UNCERTAIN = "uncertain"

    def __init__(
        self,
        metrics: LinkMetrics,
        congestion_queue_threshold_ms: float = 40.0,
        weak_signal_threshold_dbm: float = -80.0,
    ) -> None:
        if congestion_queue_threshold_ms <= 0:
            raise ValueError("congestion_queue_threshold_ms must be > 0")
        self.metrics = metrics
        self.congestion_queue_threshold_ms = congestion_queue_threshold_ms
        self.weak_signal_threshold_dbm = weak_signal_threshold_dbm

    def classify(self) -> str:
        """Queueing delay takes priority; weak signal + low queue suggests wireless loss."""
        if self.metrics.queue_delay_ms >= self.congestion_queue_threshold_ms:
            return self.CONGESTION
        if (
            self.metrics.signal_strength_dbm <= self.weak_signal_threshold_dbm
            and self.metrics.queue_delay_ms < self.congestion_queue_threshold_ms
        ):
            return self.WIRELESS
        return self.UNCERTAIN
