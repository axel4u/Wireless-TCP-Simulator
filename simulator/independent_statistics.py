"""Welch independent-sample comparisons for unpaired channel experiments."""
from __future__ import annotations

import math
import statistics
from typing import Any

from simulator.paired_statistics import _t_critical_975, _t_two_sided_p_value

METRICS = ("completion_time_ms", "goodput_mbps", "retransmissions", "timeouts", "packets_dropped")


def independent_sample_analysis(
    rows: list[dict[str, Any]],
    baseline: str = "baseline",
    comparisons: tuple[str, ...] = ("adaptive_wireless", "adaptive_congestion"),
) -> list[dict[str, Any]]:
    """Welch t-tests and Welch-Satterthwaite 95% CIs; seeds are independent groups."""
    report = []
    for comparison in comparisons:
        base_rows = [r for r in rows if r["scenario"] == baseline and r["delivery_success"]]
        comp_rows = [r for r in rows if r["scenario"] == comparison and r["delivery_success"]]
        for metric in METRICS:
            a = [float(r[metric]) for r in base_rows if math.isfinite(float(r[metric]))]
            b = [float(r[metric]) for r in comp_rows if math.isfinite(float(r[metric]))]
            n1, n2 = len(a), len(b)
            mean1 = statistics.mean(a) if n1 else math.nan
            mean2 = statistics.mean(b) if n2 else math.nan
            var1 = statistics.variance(a) if n1 > 1 else math.nan
            var2 = statistics.variance(b) if n2 > 1 else math.nan
            delta = mean2 - mean1 if n1 and n2 else math.nan
            if n1 > 1 and n2 > 1:
                v1, v2 = var1 / n1, var2 / n2
                se2 = v1 + v2
                df = se2 * se2 / (v1 * v1 / (n1 - 1) + v2 * v2 / (n2 - 1)) if se2 else n1 + n2 - 2
                se = math.sqrt(se2)
                t_value = delta / se if se else (0.0 if delta == 0 else math.copysign(math.inf, delta))
                critical = _t_critical_975(max(1, int(df)))
                low, high = delta - critical * se, delta + critical * se
                p_value = _t_two_sided_p_value(abs(t_value), max(1, int(df)))
            else:
                df = se = t_value = low = high = p_value = math.nan
            report.append({
                "comparison": comparison,
                "metric": metric,
                "baseline_successful_runs": n1,
                "comparison_successful_runs": n2,
                "baseline_mean": mean1,
                "comparison_mean": mean2,
                "mean_difference_comparison_minus_baseline": delta,
                "welch_degrees_freedom": df,
                "standard_error": se,
                "ci95_low_difference": low,
                "ci95_high_difference": high,
                "welch_t_statistic": t_value,
                "welch_t_p_value_two_sided": p_value,
                "note": "Unpaired Welch comparison of independent scenario runs; successful runs only.",
            })
    return report
