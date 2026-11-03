import pytest

from simulator.channel import WirelessChannel
from simulator.congestion_control import CongestionController
from simulator.event_scheduler import EventScheduler
from simulator.receiver import Receiver
from simulator.sender import Sender


def build_simulation(loss=0.0, seed=2, rto=20.0, retries=10,
                     initial_cwnd=1.0, ssthresh=8.0):
    scheduler = EventScheduler()
    channel = WirelessChannel(scheduler, loss_probability=loss, delay_ms=5, seed=seed)
    receiver = Receiver(channel)
    sender = Sender(channel, receiver, scheduler, rto, retries,
                    initial_cwnd, ssthresh)
    return scheduler, channel, receiver, sender


def test_sender_completes_loss_free_batch_and_grows_window():
    scheduler, _, receiver, sender = build_simulation()
    sender.send_batch(8)
    scheduler.run()
    assert receiver.delivered_count == 8
    assert sender.unique_acked_count == 8
    assert sender.is_complete
    assert sender.retransmission_count == 0
    assert sender.cwnd_packets > 1.0


def test_sender_retransmits_until_data_and_ack_are_delivered():
    scheduler, _, receiver, sender = build_simulation(loss=0.35, seed=7, rto=20, retries=10)
    sender.send_batch(5)
    scheduler.run()
    assert sender.is_complete
    assert receiver.delivered_count == 5
    assert sender.unique_acked_count == 5
    assert sender.retransmission_count > 0


def test_sender_reports_failure_when_every_transmission_is_lost():
    scheduler, _, _, sender = build_simulation(loss=1.0, rto=10, retries=2)
    sender.send_batch(1)
    with pytest.raises(RuntimeError, match="exceeded 2 retransmissions"):
        scheduler.run()
    assert sender.failed


def test_invalid_rto_is_rejected():
    scheduler, channel, receiver, _ = build_simulation()
    with pytest.raises(ValueError):
        Sender(channel, receiver, scheduler, retransmission_timeout_ms=0)


def test_initial_congestion_window_controls_first_burst():
    scheduler, channel, _, sender = build_simulation(initial_cwnd=4)
    sender.send_batch(10)
    assert channel.sent_count == 4
    assert len(sender.outstanding) == 4


def test_timeout_reduces_window_and_returns_to_slow_start():
    controller = CongestionController(initial_cwnd_packets=6, initial_ssthresh_packets=12)
    controller.on_timeout(flight_size=6)
    assert controller.cwnd_packets == 1
    assert controller.ssthresh_packets == 3
    assert controller.state == CongestionController.SLOW_START


def test_three_duplicate_acks_trigger_fast_retransmit_and_recovery():
    controller = CongestionController(initial_cwnd_packets=8, initial_ssthresh_packets=12)
    assert not controller.on_duplicate_ack(7, 8)
    assert not controller.on_duplicate_ack(7, 8)
    assert controller.on_duplicate_ack(7, 8)
    assert controller.ssthresh_packets == 4
    assert controller.cwnd_packets == 7
    assert controller.state == CongestionController.FAST_RECOVERY


def test_congestion_avoidance_grows_linearly():
    controller = CongestionController(initial_cwnd_packets=8, initial_ssthresh_packets=8)
    controller.on_new_ack(1)
    assert controller.state == CongestionController.CONGESTION_AVOIDANCE
    assert controller.cwnd_packets == pytest.approx(8.125)
