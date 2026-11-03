"""Tests for the multi-seed experiment runner."""
import math

from run_experiments import run_one, summarize


def test_zero_loss_run_completes_and_goodput_is_in_mbps():
    row = run_one("baseline", seed=3, packets=1, loss=0.0)

    assert row["delivery_success"] is True
    assert row["packets_delivered"] == 1
    assert row["completion_time_ms"] == 50.0
    # 1,000-byte packet / 0.05 seconds = 0.16 megabits per second.
    assert math.isclose(row["goodput_mbps"], 0.16)


def test_adaptive_scenarios_exercise_the_expected_recovery_branch():
    wireless = run_one(
        "adaptive_wireless", seed=7, packets=30, loss=0.10,
        wireless_queue_delay_ms=5.0,
    )
    congestion = run_one(
        "adaptive_congestion", seed=7, packets=30, loss=0.10,
        congestion_queue_delay_ms=80.0,
    )

    assert wireless["delivery_success"] is True
    assert wireless["wireless_recoveries"] == wireless["timeouts"]
    assert wireless["congestion_recoveries"] == 0
    assert congestion["delivery_success"] is True
    assert congestion["wireless_recoveries"] == 0
    assert congestion["congestion_recoveries"] == congestion["timeouts"]


def test_same_seed_and_configuration_are_repeatable():
    first = run_one("baseline", seed=11, packets=12, loss=0.10)
    second = run_one("baseline", seed=11, packets=12, loss=0.10)

    for key in (
        "packets_delivered", "retransmissions", "timeouts",
        "packets_dropped", "completion_time_ms", "final_cwnd_packets",
    ):
        assert first[key] == second[key]


def test_summary_reports_success_rate_and_sample_statistics():
    rows = [
        run_one("baseline", seed=1, packets=5, loss=0.0),
        run_one("baseline", seed=2, packets=5, loss=0.0),
        run_one("adaptive_wireless", seed=1, packets=5, loss=0.0),
    ]

    summary = summarize(rows)
    baseline = next(item for item in summary if item["scenario"] == "baseline")
    wireless = next(item for item in summary if item["scenario"] == "adaptive_wireless")

    assert baseline["runs"] == 2
    assert baseline["successful_runs"] == 2
    assert baseline["delivery_success_rate_pct"] == 100.0
    assert baseline["std_completion_time_ms"] >= 0.0
    assert wireless["runs"] == 1
    assert wireless["std_completion_time_ms"] == 0.0
