"""Receiver with out-of-order buffering and cumulative acknowledgements."""
from __future__ import annotations

from simulator.channel import WirelessChannel
from simulator.packet import Packet, PacketType


class Receiver:
    def __init__(self, channel: WirelessChannel) -> None:
        self.channel = channel
        self.next_expected_seq = 0
        self.buffered_sequences: set[int] = set()
        self.delivered_sequences: set[int] = set()

    @property
    def delivered_count(self) -> int:
        return len(self.delivered_sequences)

    def receive(self, packet: Packet, on_ack: object) -> None:
        if packet.packet_type is not PacketType.DATA:
            raise ValueError("receiver expects DATA packets")
        if packet.sequence_number >= self.next_expected_seq:
            self.buffered_sequences.add(packet.sequence_number)
            while self.next_expected_seq in self.buffered_sequences:
                self.buffered_sequences.remove(self.next_expected_seq)
                self.delivered_sequences.add(self.next_expected_seq)
                self.next_expected_seq += 1

        ack = Packet(PacketType.ACK, self.next_expected_seq, 40,
                     self.channel.scheduler.now_ms)
        self.channel.transmit(ack, on_ack)  # type: ignore[arg-type]
