import pytest

from simulator.adaptive_policy import AdaptiveRecoveryPolicy, LinkMetrics


def test_weak_signal_and_low_queue_delay_indicate_wireless_impairment():
    policy = AdaptiveRecoveryPolicy(LinkMetrics(signal_strength_dbm=-92, queue_delay_ms=5))
    assert policy.classify() == AdaptiveRecoveryPolicy.WIRELESS


def test_high_queue_delay_takes_priority_as_congestion_evidence():
    policy = AdaptiveRecoveryPolicy(LinkMetrics(signal_strength_dbm=-95, queue_delay_ms=60))
    assert policy.classify() == AdaptiveRecoveryPolicy.CONGESTION


def test_good_signal_and_low_queue_delay_are_uncertain():
    policy = AdaptiveRecoveryPolicy(LinkMetrics(signal_strength_dbm=-60, queue_delay_ms=5))
    assert policy.classify() == AdaptiveRecoveryPolicy.UNCERTAIN


def test_invalid_queue_delay_is_rejected():
    with pytest.raises(ValueError):
        LinkMetrics(queue_delay_ms=-1)


def test_invalid_congestion_threshold_is_rejected():
    with pytest.raises(ValueError):
        AdaptiveRecoveryPolicy(LinkMetrics(), congestion_queue_threshold_ms=0)
