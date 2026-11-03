"""TCP sender with a sliding window and a simplified TCP NewReno baseline."""
from __future__ import annotations

from dataclasses import dataclass

from simulator.channel import WirelessChannel
from simulator.congestion_control import CongestionController
from simulator.event_scheduler import EventScheduler
from simulator.packet import Packet, PacketType
from simulator.adaptive_policy import AdaptiveRecoveryPolicy
from simulator.receiver import Receiver


@dataclass
class _OutstandingPacket:
    packet: Packet
    transmissions: int = 1


class Sender:
    def __init__(
        self,
        channel: WirelessChannel,
        receiver: Receiver,
        scheduler: EventScheduler,
        retransmission_timeout_ms: float = 100.0,
        max_retransmissions: int = 20,
        initial_cwnd_packets: float = 1.0,
        initial_ssthresh_packets: float = 8.0,
        adaptive_policy: AdaptiveRecoveryPolicy | None = None,
    ) -> None:
        if retransmission_timeout_ms <= 0:
            raise ValueError("retransmission_timeout_ms must be > 0")
        if max_retransmissions < 0:
            raise ValueError("max_retransmissions cannot be negative")
        self.channel = channel
        self.receiver = receiver
        self.scheduler = scheduler
        self.retransmission_timeout_ms = retransmission_timeout_ms
        self.max_retransmissions = max_retransmissions
        self.adaptive_policy = adaptive_policy
        self.adaptive_decisions: list[tuple[float, str, str]] = []
        self.wireless_recovery_count = 0
        self.congestion_recovery_count = 0
        self.congestion = CongestionController(
            initial_cwnd_packets, initial_ssthresh_packets
        )
        self.acked_sequences: set[int] = set()
        self.outstanding: dict[int, _OutstandingPacket] = {}
        self.retransmission_count = 0
        self.timeout_count = 0
        self.failed = False
        self._packet_count = 0
        self._packet_size_bytes = 1000
        self._next_sequence = 0
        self._last_ack = 0
        self._timer_id: int | None = None
        self._timer_sequence: int | None = None
        self.window_history: list[tuple[float, float, str]] = [
            (scheduler.now_ms, self.congestion.cwnd_packets, self.congestion.state)
        ]

    def send_batch(self, packet_count: int, packet_size_bytes: int = 1000) -> None:
        if packet_count < 1:
            raise ValueError("packet_count must be >= 1")
        if packet_size_bytes < 1:
            raise ValueError("packet_size_bytes must be >= 1")
        if self._packet_count or self.outstanding:
            raise RuntimeError("Sender instances support one batch per simulation")
        self._packet_count = packet_count
        self._packet_size_bytes = packet_size_bytes
        self._fill_window()

    def _record_window(self) -> None:
        snapshot = (self.scheduler.now_ms, self.congestion.cwnd_packets,
                    self.congestion.state)
        if not self.window_history or self.window_history[-1][1:] != snapshot[1:]:
            self.window_history.append(snapshot)

    def _fill_window(self) -> None:
        while (
            self._next_sequence < self._packet_count
            and len(self.outstanding) < max(1, int(self.congestion.cwnd_packets))
        ):
            seq = self._next_sequence
            self._next_sequence += 1
            packet = Packet(PacketType.DATA, seq, self._packet_size_bytes,
                            self.scheduler.now_ms)
            self.outstanding[seq] = _OutstandingPacket(packet)
            self.channel.transmit(packet, self._on_data_delivery)
        self._arm_timer()

    def _on_data_delivery(self, packet: Packet) -> None:
        self.receiver.receive(packet, self._on_ack_delivery)

    def _arm_timer(self, force_restart: bool = False) -> None:
        oldest = min(self.outstanding) if self.outstanding else None
        if (
            not force_restart
            and oldest == self._timer_sequence
            and self._timer_id is not None
        ):
            return
        if self._timer_id is not None:
            self.scheduler.cancel(self._timer_id)
        self._timer_id = None
        self._timer_sequence = oldest
        if oldest is not None:
            self._timer_id = self.scheduler.schedule(
                self.retransmission_timeout_ms,
                lambda seq=oldest: self._on_timeout(seq),
            )

    def _retransmit(self, sequence_number: int) -> None:
        state = self.outstanding.get(sequence_number)
        if state is None:
            return
        if state.transmissions > self.max_retransmissions:
            self.failed = True
            raise RuntimeError(
                f"delivery failed: packet {sequence_number} exceeded "
                f"{self.max_retransmissions} retransmissions"
            )
        state.transmissions += 1
        self.retransmission_count += 1
        state.packet = Packet(
            PacketType.DATA, sequence_number, state.packet.size_bytes,
            self.scheduler.now_ms, retransmission=True,
        )
        self.channel.transmit(state.packet, self._on_data_delivery)

    def _on_ack_delivery(self, packet: Packet) -> None:
        if packet.packet_type is not PacketType.ACK:
            return
        ack_number = packet.sequence_number
        if ack_number < self._last_ack:
            return

        newly_acked = [seq for seq in self.outstanding if seq < ack_number]
        if newly_acked:
            old_timer_sequence = self._timer_sequence
            for seq in newly_acked:
                self.outstanding.pop(seq, None)
                self.acked_sequences.add(seq)
            self._last_ack = ack_number

            if self.congestion.state == CongestionController.FAST_RECOVERY:
                if ack_number <= self.congestion.recover_sequence:
                    self.congestion.on_partial_ack(len(newly_acked))
                    if self.outstanding:
                        self._retransmit(min(self.outstanding))
                else:
                    self.congestion.on_full_ack()
            else:
                self.congestion.on_new_ack(len(newly_acked))
            self._record_window()

            if old_timer_sequence in newly_acked:
                if self._timer_id is not None:
                    self.scheduler.cancel(self._timer_id)
                self._timer_id = None
                self._timer_sequence = None
            self._arm_timer()
            self._fill_window()
            return

        if ack_number == self._last_ack and self.outstanding:
            fast_retransmit = self.congestion.on_duplicate_ack(
                self._next_sequence - 1, len(self.outstanding)
            )
            self._record_window()
            if fast_retransmit:
                self._retransmit(min(self.outstanding))
                # Fast retransmit starts a fresh RTO for the oldest
                # outstanding segment rather than retaining its old deadline.
                self._arm_timer(force_restart=True)
            elif self.congestion.state == CongestionController.FAST_RECOVERY:
                self._fill_window()

    def _on_timeout(self, sequence_number: int) -> None:
        self._timer_id = None
        self._timer_sequence = None
        if not self.outstanding or min(self.outstanding) != sequence_number:
            self._arm_timer()
            return
        self.timeout_count += 1
        decision = (
            self.adaptive_policy.classify()
            if self.adaptive_policy is not None
            else AdaptiveRecoveryPolicy.UNCERTAIN
        )
        if self.adaptive_policy is not None:
            self.adaptive_decisions.append((self.scheduler.now_ms, decision, "timeout"))
        if decision == AdaptiveRecoveryPolicy.WIRELESS:
            # Likely wireless impairment: retransmit without shrinking cwnd.
            self.wireless_recovery_count += 1
        else:
            # Congestion or uncertain evidence keeps the conservative fallback.
            self.congestion_recovery_count += 1
            self.congestion.on_timeout(len(self.outstanding))
        self._record_window()
        self._retransmit(sequence_number)
        self._arm_timer()

    @property
    def unique_acked_count(self) -> int:
        return len(self.acked_sequences)

    @property
    def is_complete(self) -> bool:
        return self._packet_count > 0 and self.unique_acked_count == self._packet_count

    @property
    def cwnd_packets(self) -> float:
        return self.congestion.cwnd_packets

    @property
    def ssthresh_packets(self) -> float:
        return self.congestion.ssthresh_packets
