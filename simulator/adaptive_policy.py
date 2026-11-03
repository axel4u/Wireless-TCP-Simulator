"""Rule-based classification of observable link conditions for adaptive recovery.

The policy never receives the channel's hidden random drop decision or the
actual cause of an individual lost packet.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class LinkMetrics:
    """Observable or simulated link measurements supplied to the sender."""

    signal_strength_dbm: float = -65.0
    queue_delay_ms: float = 0.0
    link_retransmissions: int = 0

    def __post_init__(self) -> None:
        if not math.isfinite(self.signal_strength_dbm):
            raise ValueError("signal_strength_dbm must be finite")
        if not math.isfinite(self.queue_delay_ms) or self.queue_delay_ms < 0:
            raise ValueError("queue_delay_ms must be finite and non-negative")
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
        if not math.isfinite(congestion_queue_threshold_ms) or congestion_queue_threshold_ms <= 0:
            raise ValueError("congestion_queue_threshold_ms must be finite and > 0")
        if not math.isfinite(weak_signal_threshold_dbm):
            raise ValueError("weak_signal_threshold_dbm must be finite")
        self.metrics = metrics
        self.congestion_queue_threshold_ms = congestion_queue_threshold_ms
        self.weak_signal_threshold_dbm = weak_signal_threshold_dbm

    def classify(self) -> str:
        """Queueing delay takes priority; weak signal + low queue suggests wireless loss."""
        # Congestion evidence always wins, even when signal strength is poor.
        if self.metrics.queue_delay_ms >= self.congestion_queue_threshold_ms:
            return self.CONGESTION
        if self.metrics.signal_strength_dbm <= self.weak_signal_threshold_dbm:
            return self.WIRELESS
        return self.UNCERTAIN
