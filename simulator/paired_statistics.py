"""Paired statistical analysis using only the Python standard library."""
from __future__ import annotations

import math
import statistics
from typing import Any


PAIRED_METRICS = (
    "completion_time_ms", "goodput_mbps", "retransmissions", "timeouts",
    "packets_dropped", "final_cwnd_packets", "final_ssthresh_packets",
)


def _beta_continued_fraction(a: float, b: float, x: float) -> float:
    """Evaluate the incomplete-beta continued fraction (Numerical Recipes)."""
    max_iter, eps, tiny = 300, 3e-14, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _regularized_beta(x: float, a: float, b: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + a * math.log(x) + b * math.log1p(-x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _beta_continued_fraction(a, b, x) / a
    return 1.0 - front * _beta_continued_fraction(b, a, 1.0 - x) / b


def _t_two_sided_p_value(t_value: float, degrees_freedom: int) -> float:
    x = degrees_freedom / (degrees_freedom + t_value * t_value)
    return min(1.0, _regularized_beta(x, degrees_freedom / 2.0, 0.5))


def _t_critical_975(degrees_freedom: int) -> float:
    low, high = 0.0, 1.0
    while _t_two_sided_p_value(high, degrees_freedom) > 0.05:
        high *= 2.0
    for _ in range(90):
        mid = (low + high) / 2.0
        if _t_two_sided_p_value(mid, degrees_freedom) > 0.05:
            low = mid
        else:
            high = mid
    return (low + high) / 2.0


def _exact_sign_test(wins: int, losses: int) -> float:
    """Two-sided exact binomial sign test; ties are excluded."""
    n = wins + losses
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(wins, losses) + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def paired_analysis(
    rows: list[dict[str, Any]],
    baseline_name: str = "baseline",
    comparison_names: tuple[str, ...] = ("adaptive_wireless", "adaptive_congestion"),
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return per-seed paired rows and per-metric statistical report rows.

    Deltas are comparison minus baseline. Improvement direction is lower for
    time/count metrics and higher for goodput. Performance tests use only seeds
    where both paired runs succeeded; recovery/cwnd metrics are descriptive.
    """
    by_key = {(row["scenario"], int(row["seed"])): row for row in rows}
    paired_rows: list[dict[str, Any]] = []
    report: list[dict[str, Any]] = []

    for comparison in comparison_names:
        common_seeds = sorted(
            seed for scenario, seed in by_key
            if scenario == baseline_name and (comparison, seed) in by_key
        )
        complete_pairs = [
            (seed, by_key[(baseline_name, seed)], by_key[(comparison, seed)])
            for seed in common_seeds
        ]
        successful = [
            pair for pair in complete_pairs
            if pair[1]["delivery_success"] and pair[2]["delivery_success"]
        ]

        for seed, base, comp in complete_pairs:
            item: dict[str, Any] = {
                "comparison": comparison,
                "seed": seed,
                "baseline_success": base["delivery_success"],
                "comparison_success": comp["delivery_success"],
            }
            for metric in PAIRED_METRICS:
                b, c = float(base[metric]), float(comp[metric])
                item[f"baseline_{metric}"] = b
                item[f"comparison_{metric}"] = c
                item[f"delta_{metric}"] = c - b if math.isfinite(b) and math.isfinite(c) else math.nan
            paired_rows.append(item)

        for metric in PAIRED_METRICS:
            diffs = [
                float(comp[metric]) - float(base[metric])
                for _, base, comp in successful
                if math.isfinite(float(base[metric])) and math.isfinite(float(comp[metric]))
            ]
            n = len(diffs)
            mean_diff = statistics.mean(diffs) if n else math.nan
            median_diff = statistics.median(diffs) if n else math.nan
            wins = sum(d < 0 for d in diffs) if metric != "goodput_mbps" else sum(d > 0 for d in diffs)
            losses = sum(d > 0 for d in diffs) if metric != "goodput_mbps" else sum(d < 0 for d in diffs)
            ties = sum(d == 0 for d in diffs)
            if n > 1:
                sd = statistics.stdev(diffs)
                se = sd / math.sqrt(n)
                t_stat = mean_diff / se if se else (0.0 if mean_diff == 0 else math.copysign(math.inf, mean_diff))
                critical = _t_critical_975(n - 1)
                ci_low = mean_diff - critical * se
                ci_high = mean_diff + critical * se
                t_p = _t_two_sided_p_value(abs(t_stat), n - 1)
            else:
                sd = se = t_stat = ci_low = ci_high = t_p = math.nan
            report.append({
                "comparison": comparison,
                "metric": metric,
                "paired_successful_seeds": n,
                "matched_seeds": len(complete_pairs),
                "mean_delta_comparison_minus_baseline": mean_diff,
                "median_delta_comparison_minus_baseline": median_diff,
                "sample_std_delta": sd,
                "ci95_low_delta": ci_low,
                "ci95_high_delta": ci_high,
                "paired_t_statistic": t_stat,
                "paired_t_p_value_two_sided": t_p,
                "improved_seeds": wins,
                "equal_seeds": ties,
                "worsened_seeds": losses,
                "exact_sign_test_p_value_two_sided": _exact_sign_test(wins, losses),
                "note": "Goodput improvement means positive delta; all other listed metrics use negative delta. Paired tests are conditional on both runs succeeding.",
            })
    return paired_rows, report
