"""Tests for unpaired Welch analysis."""
from simulator.independent_statistics import independent_sample_analysis


def test_welch_report_compares_independent_scenario_samples():
    rows = []
    for seed, value in enumerate((100.0, 110.0, 90.0, 105.0), start=1):
        rows.append({
            "scenario": "baseline", "seed": seed, "delivery_success": True,
            "completion_time_ms": value, "goodput_mbps": 0.5,
            "retransmissions": 3, "timeouts": 2, "packets_dropped": 4,
        })
    for seed, value in enumerate((80.0, 85.0, 90.0, 75.0), start=11):
        rows.append({
            "scenario": "adaptive_wireless", "seed": seed, "delivery_success": True,
            "completion_time_ms": value, "goodput_mbps": 0.6,
            "retransmissions": 2, "timeouts": 1, "packets_dropped": 4,
        })

    report = independent_sample_analysis(rows)
    completion = next(row for row in report if row["metric"] == "completion_time_ms")
    assert completion["baseline_successful_runs"] == 4
    assert completion["comparison_successful_runs"] == 4
    assert completion["mean_difference_comparison_minus_baseline"] < 0
    assert completion["ci95_low_difference"] < completion["ci95_high_difference"]
    assert 0 <= completion["welch_t_p_value_two_sided"] <= 1
