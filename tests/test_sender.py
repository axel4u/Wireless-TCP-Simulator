import pytest

from simulator.channel import WirelessChannel
from simulator.event_scheduler import EventScheduler
from simulator.receiver import Receiver
from simulator.packet import Packet, PacketType
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


def test_sender_enters_fast_recovery_after_three_duplicate_acks():
    scheduler, _, receiver, sender = build_simulation(
        loss=0.2, seed=1, rto=20, retries=10, initial_cwnd=6, ssthresh=12
    )
    sender.send_batch(6)
    scheduler.run()
    assert sender.is_complete
    assert receiver.delivered_count == 6
    assert any(state == "fast_recovery" for _, _, state in sender.window_history)



def test_fast_retransmit_can_restart_oldest_packet_timer():
    scheduler, _, _, sender = build_simulation()
    sender.send_batch(1)
    original_timer_id = sender._timer_id
    assert original_timer_id is not None

    sender._arm_timer(force_restart=True)

    assert sender._timer_id is not None
    assert sender._timer_id != original_timer_id
    assert original_timer_id in scheduler._cancelled



def _enter_sender_fast_recovery(sender):
    """Drive the sender through three duplicate cumulative ACKs."""
    duplicate_ack = Packet(PacketType.ACK, 0, 40, sender.scheduler.now_ms)
    sender._on_ack_delivery(duplicate_ack)
    sender._on_ack_delivery(duplicate_ack)
    sender._on_ack_delivery(duplicate_ack)
    assert sender.congestion.state == "fast_recovery"


def test_timeout_during_fast_recovery_resets_sender_recovery_state():
    scheduler, _, _, sender = build_simulation(initial_cwnd=6, ssthresh=12)
    sender.send_batch(6)
    _enter_sender_fast_recovery(sender)

    oldest = min(sender.outstanding)
    sender._on_timeout(oldest)

    assert sender.congestion.state == "slow_start"
    assert sender.cwnd_packets == 1
    assert sender.congestion.recover_sequence == -1
    assert sender.timeout_count == 1


def test_partial_ack_retransmits_next_missing_packet_and_stays_in_recovery():
    scheduler, _, _, sender = build_simulation(initial_cwnd=6, ssthresh=12)
    sender.send_batch(6)
    _enter_sender_fast_recovery(sender)

    # ACK 1 cumulatively acknowledges packet 0 but not the recovery boundary.
    partial_ack = Packet(PacketType.ACK, 1, 40, scheduler.now_ms)
    sender._on_ack_delivery(partial_ack)

    assert sender.congestion.state == "fast_recovery"
    assert 0 in sender.acked_sequences
    assert min(sender.outstanding) == 1
    assert sender.retransmission_count == 2  # fast retransmit + partial-ACK retransmit


def test_full_ack_exits_sender_fast_recovery():
    scheduler, _, _, sender = build_simulation(initial_cwnd=6, ssthresh=12)
    sender.send_batch(6)
    _enter_sender_fast_recovery(sender)

    # ACK 6 advances beyond recover_sequence 5.
    full_ack = Packet(PacketType.ACK, 6, 40, scheduler.now_ms)
    sender._on_ack_delivery(full_ack)

    assert sender.is_complete
    assert sender.congestion.state == "congestion_avoidance"
    assert sender.cwnd_packets == sender.ssthresh_packets
    assert not sender.outstanding
