"""TCP NewReno congestion-window state and growth rules.

The window is measured in whole/ fractional DATA packets (MSS units), which
keeps the educational simulator's congestion-control arithmetic readable.
"""
from __future__ import annotations


class CongestionController:
    SLOW_START = "slow_start"
    CONGESTION_AVOIDANCE = "congestion_avoidance"
    FAST_RECOVERY = "fast_recovery"

    def __init__(self, initial_cwnd_packets: float = 1.0,
                 initial_ssthresh_packets: float = 8.0) -> None:
        if initial_cwnd_packets < 1:
            raise ValueError("initial_cwnd_packets must be >= 1")
        if initial_ssthresh_packets < 2:
            raise ValueError("initial_ssthresh_packets must be >= 2")
        self.cwnd_packets = float(initial_cwnd_packets)
        self.ssthresh_packets = float(initial_ssthresh_packets)
        self.state = (
            self.SLOW_START if self.cwnd_packets < self.ssthresh_packets
            else self.CONGESTION_AVOIDANCE
        )
        self.duplicate_acks = 0
        self.recover_sequence = -1

    def on_new_ack(self, newly_acked: int) -> None:
        if newly_acked <= 0:
            return
        self.duplicate_acks = 0
        if self.state == self.SLOW_START:
            self.cwnd_packets += newly_acked
            if self.cwnd_packets >= self.ssthresh_packets:
                self.state = self.CONGESTION_AVOIDANCE
        elif self.state == self.CONGESTION_AVOIDANCE:
            self.cwnd_packets += newly_acked / self.cwnd_packets

    def on_duplicate_ack(self, highest_sent_sequence: int,
                         flight_size: int) -> bool:
        """Record a duplicate ACK; return True when fast retransmit is due."""
        self.duplicate_acks += 1
        if self.state == self.FAST_RECOVERY:
            self.cwnd_packets += 1.0
            return False
        if self.duplicate_acks == 3:
            self.ssthresh_packets = max(float(flight_size) / 2.0, 2.0)
            self.cwnd_packets = self.ssthresh_packets + 3.0
            self.recover_sequence = highest_sent_sequence
            self.state = self.FAST_RECOVERY
            return True
        return False

    def on_partial_ack(self) -> None:
        """NewReno partial ACK: remain in recovery and deflate by retransmitting."""
        self.cwnd_packets = self.ssthresh_packets + 3.0
        self.state = self.FAST_RECOVERY
        self.duplicate_acks = 0

    def on_full_ack(self) -> None:
        self.cwnd_packets = self.ssthresh_packets
        self.state = self.CONGESTION_AVOIDANCE
        self.duplicate_acks = 0

    def on_timeout(self, flight_size: int) -> None:
        self.ssthresh_packets = max(float(flight_size) / 2.0, 2.0)
        self.cwnd_packets = 1.0
        self.state = self.SLOW_START
        self.duplicate_acks = 0
        self.recover_sequence = -1
