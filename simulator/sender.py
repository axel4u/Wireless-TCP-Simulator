"""Reliable stop-and-wait sender with cumulative ACKs and retransmission timers.

This milestone models reliability only. Congestion control and a TCP congestion
window are intentionally deferred to the next milestone.
"""
from __future__ import annotations

from dataclasses import dataclass

from simulator.channel import WirelessChannel
from simulator.event_scheduler import EventScheduler
from simulator.packet import Packet, PacketType
from simulator.receiver import Receiver


@dataclass
class _OutstandingPacket:
    packet: Packet
    transmissions: int = 1
    timer_id: int | None = None


class Sender:
    def __init__(
        self,
        channel: WirelessChannel,
        receiver: Receiver,
        scheduler: EventScheduler,
        retransmission_timeout_ms: float = 100.0,
        max_retransmissions: int = 20,
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
        self.acked_sequences: set[int] = set()
        self.outstanding: dict[int, _OutstandingPacket] = {}
        self.retransmission_count = 0
        self.timeout_count = 0
        self.failed = False
        self._packet_count = 0

    def send_batch(self, packet_count: int, packet_size_bytes: int = 1000) -> None:
        if packet_count < 1:
            raise ValueError("packet_count must be >= 1")
        if packet_size_bytes < 1:
            raise ValueError("packet_size_bytes must be >= 1")
        if self._packet_count or self.outstanding:
            raise RuntimeError("Sender instances support one batch per simulation")
        self._packet_count = packet_count

        # This milestone deliberately uses a one-packet window: it isolates
        # reliable delivery before congestion/window behavior is introduced.
        self._send_new_packet(0, packet_size_bytes)

    def _send_new_packet(self, sequence_number: int, size_bytes: int) -> None:
        packet = Packet(PacketType.DATA, sequence_number, size_bytes,
                        self.scheduler.now_ms)
        state = _OutstandingPacket(packet=packet)
        self.outstanding[sequence_number] = state
        self._transmit_state(sequence_number, state)

    def _transmit_state(self, sequence_number: int, state: _OutstandingPacket) -> None:
        self.channel.transmit(state.packet, self._on_data_delivery)
        if state.timer_id is not None:
            self.scheduler.cancel(state.timer_id)
        state.timer_id = self.scheduler.schedule(
            self.retransmission_timeout_ms,
            lambda seq=sequence_number, expected=state: self._on_timeout(seq, expected),
        )

    def _on_data_delivery(self, packet: Packet) -> None:
        self.receiver.receive(packet, self._on_ack_delivery)

    def _on_ack_delivery(self, packet: Packet) -> None:
        if packet.packet_type is not PacketType.ACK:
            return
        # ACK N cumulatively acknowledges all DATA sequence numbers below N.
        newly_acked = [
            seq for seq in self.outstanding
            if seq < packet.sequence_number
        ]
        for seq in newly_acked:
            state = self.outstanding.pop(seq)
            if state.timer_id is not None:
                self.scheduler.cancel(state.timer_id)
            self.acked_sequences.add(seq)

        if newly_acked and len(self.acked_sequences) < self._packet_count:
            next_seq = max(self.acked_sequences, default=-1) + 1
            if next_seq not in self.outstanding and next_seq < self._packet_count:
                size = next(iter(self.outstanding.values())).packet.size_bytes if self.outstanding else 1000
                self._send_new_packet(next_seq, size)

    def _on_timeout(self, sequence_number: int, expected_state: _OutstandingPacket) -> None:
        current = self.outstanding.get(sequence_number)
        if current is not expected_state:
            return
        if current.transmissions > self.max_retransmissions:
            self.failed = True
            raise RuntimeError(
                f"delivery failed: packet {sequence_number} exceeded "
                f"{self.max_retransmissions} retransmissions"
            )

        self.timeout_count += 1
        self.retransmission_count += 1
        current.transmissions += 1
        current.packet = Packet(
            packet_type=PacketType.DATA,
            sequence_number=sequence_number,
            size_bytes=current.packet.size_bytes,
            created_at_ms=self.scheduler.now_ms,
            retransmission=True,
        )
        self._transmit_state(sequence_number, current)

    @property
    def unique_acked_count(self) -> int:
        return len(self.acked_sequences)

    @property
    def is_complete(self) -> bool:
        return self._packet_count > 0 and self.unique_acked_count == self._packet_count
