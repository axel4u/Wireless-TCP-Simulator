import pytest

from simulator.congestion_control import CongestionController


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
