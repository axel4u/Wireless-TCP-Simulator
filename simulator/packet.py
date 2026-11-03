"""Packet data structures used by the simulation."""
from dataclasses import dataclass
from enum import Enum


class PacketType(str, Enum):
    DATA = "DATA"
    ACK = "ACK"


@dataclass(frozen=True, slots=True)
class Packet:
    packet_type: PacketType
    sequence_number: int
    size_bytes: int
    created_at_ms: float
    retransmission: bool = False

    def __post_init__(self) -> None:
        if self.sequence_number < 0:
            raise ValueError("sequence_number cannot be negative")
        if self.size_bytes < 0:
            raise ValueError("size_bytes cannot be negative")
