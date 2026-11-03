import math

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


def test_queue_delay_exactly_at_threshold_is_congestion():
    policy = AdaptiveRecoveryPolicy(
        LinkMetrics(signal_strength_dbm=-95, queue_delay_ms=40),
        congestion_queue_threshold_ms=40,
    )
    assert policy.classify() == AdaptiveRecoveryPolicy.CONGESTION


def test_weak_signal_just_below_queue_threshold_is_wireless():
    policy = AdaptiveRecoveryPolicy(
        LinkMetrics(signal_strength_dbm=-95, queue_delay_ms=39.999),
        congestion_queue_threshold_ms=40,
    )
    assert policy.classify() == AdaptiveRecoveryPolicy.WIRELESS


def test_congestion_wins_for_weak_signal_at_threshold_boundary():
    policy = AdaptiveRecoveryPolicy(
        LinkMetrics(signal_strength_dbm=-110, queue_delay_ms=40),
        congestion_queue_threshold_ms=40,
    )
    assert policy.classify() == AdaptiveRecoveryPolicy.CONGESTION


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_non_finite_signal_strength_is_rejected(value):
    with pytest.raises(ValueError, match="signal_strength_dbm must be finite"):
        LinkMetrics(signal_strength_dbm=value)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_non_finite_queue_delay_is_rejected(value):
    with pytest.raises(ValueError, match="queue_delay_ms must be finite"):
        LinkMetrics(queue_delay_ms=value)


def test_invalid_queue_delay_is_rejected():
    with pytest.raises(ValueError):
        LinkMetrics(queue_delay_ms=-1)


@pytest.mark.parametrize("value", [0, -1, math.nan, math.inf])
def test_invalid_congestion_threshold_is_rejected(value):
    with pytest.raises(ValueError):
        AdaptiveRecoveryPolicy(LinkMetrics(), congestion_queue_threshold_ms=value)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_non_finite_weak_signal_threshold_is_rejected(value):
    with pytest.raises(ValueError, match="weak_signal_threshold_dbm must be finite"):
        AdaptiveRecoveryPolicy(LinkMetrics(), weak_signal_threshold_dbm=value)
