"""Fixed-batch sender used before TCP reliability is introduced."""
from __future__ import annotations

from simulator.channel import WirelessChannel
from simulator.event_scheduler import EventScheduler
from simulator.packet import Packet, PacketType
from simulator.receiver import Receiver


class Sender:
    def __init__(self, channel: WirelessChannel, receiver: Receiver,
                 scheduler: EventScheduler) -> None:
        self.channel = channel
        self.receiver = receiver
        self.scheduler = scheduler
        self.acked_sequences: set[int] = set()

    def send_batch(self, packet_count: int, packet_size_bytes: int = 1000) -> None:
        if packet_count < 1:
            raise ValueError("packet_count must be >= 1")
        if packet_size_bytes < 1:
            raise ValueError("packet_size_bytes must be >= 1")
        for seq in range(packet_count):
            packet = Packet(PacketType.DATA, seq, packet_size_bytes,
                            self.scheduler.now_ms)
            self.channel.transmit(packet, self._on_data_delivery)

    def _on_data_delivery(self, packet: Packet) -> None:
        self.receiver.receive(packet, self._on_ack_delivery)

    def _on_ack_delivery(self, packet: Packet) -> None:
        if packet.packet_type is not PacketType.ACK:
            return
        # ACK number means the next DATA sequence number expected (cumulative ACK).
        self.acked_sequences.update(range(packet.sequence_number))

    @property
    def unique_acked_count(self) -> int:
        return len(self.acked_sequences)
