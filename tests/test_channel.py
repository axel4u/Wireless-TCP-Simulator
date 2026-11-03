from simulator.channel import WirelessChannel
from simulator.event_scheduler import EventScheduler
from simulator.packet import Packet, PacketType


def test_zero_loss_delivers_after_configured_delay():
    scheduler = EventScheduler()
    channel = WirelessChannel(scheduler, loss_probability=0, delay_ms=12, seed=1)
    packet = Packet(PacketType.DATA, 0, 1000, 0)
    received = []
    channel.transmit(packet, received.append)
    assert received == []
    scheduler.run()
    assert received == [packet]
    assert scheduler.now_ms == 12


def test_total_loss_drops_packet():
    scheduler = EventScheduler()
    channel = WirelessChannel(scheduler, loss_probability=1, delay_ms=12, seed=1)
    packet = Packet(PacketType.DATA, 0, 1000, 0)
    received = []
    channel.transmit(packet, received.append)
    scheduler.run()
    assert received == []
    assert channel.dropped_count == 1
