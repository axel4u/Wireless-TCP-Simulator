"""Tests for paired seed-level statistical analysis."""
import math

from simulator.paired_statistics import paired_analysis


def _row(scenario, seed, completion, goodput=0.5, success=True):
    return {
        "scenario": scenario,
        "seed": seed,
        "delivery_success": success,
        "completion_time_ms": completion,
        "goodput_mbps": goodput,
        "retransmissions": 2,
        "timeouts": 1,
        "packets_dropped": 3,
        "final_cwnd_packets": 4.0,
        "final_ssthresh_packets": 2.0,
    }


def test_paired_analysis_counts_faster_equal_and_slower_seeds():
    rows = []
    baseline_times = [100, 100, 100, 100]
    adaptive_times = [80, 90, 100, 110]
    for seed, (base, adaptive) in enumerate(zip(baseline_times, adaptive_times), 1):
        rows.extend([
            _row("baseline", seed, base),
            _row("adaptive_wireless", seed, adaptive),
        ])

    paired, report = paired_analysis(
        rows, comparison_names=("adaptive_wireless",)
    )
    completion = next(
        item for item in report if item["metric"] == "completion_time_ms"
    )

    assert len(paired) == 4
    assert completion["paired_successful_seeds"] == 4
    assert completion["mean_delta_comparison_minus_baseline"] == -5
    assert completion["improved_seeds"] == 2
    assert completion["equal_seeds"] == 1
    assert completion["worsened_seeds"] == 1
    assert 0 <= completion["exact_sign_test_p_value_two_sided"] <= 1
    assert completion["ci95_low_delta"] < completion["ci95_high_delta"]


def test_goodput_improvement_uses_positive_delta_direction():
    rows = [
        _row("baseline", 1, 100, goodput=0.4),
        _row("adaptive_wireless", 1, 100, goodput=0.5),
        _row("baseline", 2, 100, goodput=0.4),
        _row("adaptive_wireless", 2, 100, goodput=0.3),
    ]
    _, report = paired_analysis(rows, comparison_names=("adaptive_wireless",))
    goodput = next(item for item in report if item["metric"] == "goodput_mbps")

    assert goodput["improved_seeds"] == 1
    assert goodput["worsened_seeds"] == 1
    assert math.isclose(goodput["mean_delta_comparison_minus_baseline"], 0.0)


def test_failed_pairs_are_excluded_from_performance_tests():
    rows = [
        _row("baseline", 1, 100),
        _row("adaptive_wireless", 1, 80),
        _row("baseline", 2, 100),
        _row("adaptive_wireless", 2, math.nan, success=False),
    ]
    paired, report = paired_analysis(rows, comparison_names=("adaptive_wireless",))
    completion = next(
        item for item in report if item["metric"] == "completion_time_ms"
    )

    assert len(paired) == 2
    assert completion["matched_seeds"] == 2
    assert completion["paired_successful_seeds"] == 1
    assert math.isnan(completion["paired_t_p_value_two_sided"])
