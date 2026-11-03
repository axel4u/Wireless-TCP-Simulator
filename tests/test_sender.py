from simulator.channel import WirelessChannel
from simulator.event_scheduler import EventScheduler
from simulator.receiver import Receiver
from simulator.sender import Sender


def test_sender_and_receiver_complete_loss_free_batch():
    scheduler = EventScheduler()
    channel = WirelessChannel(scheduler, loss_probability=0, delay_ms=5, seed=2)
    receiver = Receiver(channel)
    sender = Sender(channel, receiver, scheduler)
    sender.send_batch(4)
    scheduler.run()
    assert receiver.delivered_count == 4
    assert sender.unique_acked_count == 4
