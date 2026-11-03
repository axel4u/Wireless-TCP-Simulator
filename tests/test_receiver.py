from simulator.channel import WirelessChannel
from simulator.event_scheduler import EventScheduler
from simulator.packet import Packet, PacketType
from simulator.receiver import Receiver


def test_receiver_buffers_out_of_order_and_sends_cumulative_ack():
    scheduler = EventScheduler()
    channel = WirelessChannel(scheduler, loss_probability=0, delay_ms=0, seed=1)
    receiver = Receiver(channel)
    acks = []
    receiver.receive(Packet(PacketType.DATA, 1, 100, 0), acks.append)
    scheduler.run()
    assert acks[-1].sequence_number == 0
    receiver.receive(Packet(PacketType.DATA, 0, 100, scheduler.now_ms), acks.append)
    scheduler.run()
    assert acks[-1].sequence_number == 2
    assert receiver.delivered_count == 2
