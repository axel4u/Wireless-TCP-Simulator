from simulator.adaptive_policy import AdaptiveRecoveryPolicy, LinkMetrics
from simulator.channel import WirelessChannel
from simulator.event_scheduler import EventScheduler
from simulator.receiver import Receiver
from simulator.sender import Sender


def build_adaptive_simulation(loss, signal_db, queue_delay_ms, seed=7):
    scheduler = EventScheduler()
    channel = WirelessChannel(scheduler, loss_probability=loss, delay_ms=5, seed=seed)
    receiver = Receiver(channel)
    policy = AdaptiveRecoveryPolicy(
        LinkMetrics(signal_strength_dbm=signal_db, queue_delay_ms=queue_delay_ms)
    )
    sender = Sender(
        channel, receiver, scheduler, retransmission_timeout_ms=20,
        max_retransmissions=10, initial_cwnd_packets=4,
        initial_ssthresh_packets=8, adaptive_policy=policy,
    )
    return scheduler, sender


def observe_first_timeout(scheduler, sender):
    sender.send_batch(1)
    try:
        scheduler.run(max_events=1)
    except RuntimeError:
        # A permanently lossy test channel eventually reaches the retry limit.
        pass


def test_wireless_timeout_retransmits_without_reducing_cwnd():
    scheduler, sender = build_adaptive_simulation(1.0, -95, 2)
    original_ssthresh = sender.ssthresh_packets
    observe_first_timeout(scheduler, sender)
    assert sender.wireless_recovery_count == 1
    assert sender.cwnd_packets == 4
    assert sender.ssthresh_packets == original_ssthresh
    assert sender.adaptive_decisions[0][1] == AdaptiveRecoveryPolicy.WIRELESS


def test_congestion_evidence_uses_standard_timeout_fallback():
    scheduler, sender = build_adaptive_simulation(1.0, -95, 80)
    observe_first_timeout(scheduler, sender)
    assert sender.congestion_recovery_count == 1
    assert sender.cwnd_packets == 1
    assert sender.adaptive_decisions[0][1] == AdaptiveRecoveryPolicy.CONGESTION


def test_uncertain_evidence_uses_standard_timeout_fallback():
    scheduler, sender = build_adaptive_simulation(1.0, -60, 2)
    observe_first_timeout(scheduler, sender)
    assert sender.congestion_recovery_count == 1
    assert sender.cwnd_packets == 1
    assert sender.adaptive_decisions[0][1] == AdaptiveRecoveryPolicy.UNCERTAIN
