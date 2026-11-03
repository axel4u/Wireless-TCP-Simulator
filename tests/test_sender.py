from simulator.channel import WirelessChannel
from simulator.event_scheduler import EventScheduler
from simulator.receiver import Receiver
from simulator.sender import Sender


def build_simulation(loss=0.0, seed=2, rto=20.0, retries=10):
    scheduler = EventScheduler()
    channel = WirelessChannel(scheduler, loss_probability=loss, delay_ms=5, seed=seed)
    receiver = Receiver(channel)
    sender = Sender(channel, receiver, scheduler, rto, retries)
    return scheduler, channel, receiver, sender


def test_sender_and_receiver_complete_loss_free_batch():
    scheduler, _, receiver, sender = build_simulation()
    sender.send_batch(4)
    scheduler.run()
    assert receiver.delivered_count == 4
    assert sender.unique_acked_count == 4
    assert sender.is_complete
    assert sender.retransmission_count == 0


def test_sender_retransmits_until_data_and_ack_are_delivered():
    scheduler, channel, receiver, sender = build_simulation(loss=0.35, seed=7, rto=20)
    sender.send_batch(5)
    scheduler.run()
    assert sender.is_complete
    assert receiver.delivered_count == 5
    assert sender.unique_acked_count == 5
    assert sender.retransmission_count > 0


def test_sender_reports_failure_when_every_transmission_is_lost():
    scheduler, _, _, sender = build_simulation(loss=1.0, rto=10, retries=2)
    sender.send_batch(1)
    import pytest
    with pytest.raises(RuntimeError, match="exceeded 2 retransmissions"):
        scheduler.run()
    assert sender.failed


def test_invalid_rto_is_rejected():
    import pytest
    scheduler, channel, receiver, _ = build_simulation()
    with pytest.raises(ValueError):
        Sender(channel, receiver, scheduler, retransmission_timeout_ms=0)
