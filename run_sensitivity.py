"""Run a signal-strength x queue-delay sensitivity grid for adaptive recovery."""
from __future__ import annotations

import argparse
import csv
import math
import statistics
from pathlib import Path
from typing import Any

from run_experiments import run_one
from simulator.adaptive_policy import AdaptiveRecoveryPolicy, LinkMetrics
from simulator.paired_statistics import paired_analysis


def classify_grid_point(signal_dbm: float, queue_delay_ms: float,
                        congestion_threshold_ms: float,
                        weak_signal_threshold_dbm: float) -> str:
    """Return the policy class expected from observable inputs only."""
    policy = AdaptiveRecoveryPolicy(
        LinkMetrics(signal_strength_dbm=signal_dbm,
                    queue_delay_ms=queue_delay_ms),
        congestion_queue_threshold_ms=congestion_threshold_ms,
        weak_signal_threshold_dbm=weak_signal_threshold_dbm,
    )
    return policy.classify()


def parse_values(raw: str, option: str) -> list[float]:
    try:
        values = [float(part.strip()) for part in raw.split(",")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{option} must be comma-separated numbers") from exc
    if not values or any(not math.isfinite(value) for value in values):
        raise argparse.ArgumentTypeError(f"{option} values must be finite")
    if len(set(values)) != len(values):
        raise argparse.ArgumentTypeError(f"{option} values must be unique")
    return values


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty results: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_sweep(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    detailed: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    paired_reports: list[dict[str, Any]] = []
    metrics = ("completion_time_ms", "goodput_mbps", "retransmissions", "timeouts")

    for signal in args.signals:
        for queue_delay in args.queue_delays:
            classification = classify_grid_point(
                signal, queue_delay, args.congestion_queue_threshold_ms,
                args.weak_signal_threshold_db,
            )
            paired_rows: list[dict[str, Any]] = []
            for seed in range(args.start_seed, args.start_seed + args.seeds):
                common = dict(
                    seed=seed, packets=args.packets, loss_mode="random",
                    channel_model="burst", burst_trace_mode="shared-time",
                    good_to_bad_probability=args.good_to_bad,
                    bad_to_good_probability=args.bad_to_good,
                    good_state_loss_probability=args.good_loss,
                    bad_state_loss_probability=args.bad_loss,
                    congestion_queue_threshold_ms=args.congestion_queue_threshold_ms,
                    weak_signal_threshold_dbm=args.weak_signal_threshold_db,
                )
                baseline = run_one("baseline", **common)
                adaptive = run_one(
                    "adaptive_wireless", signal_dbm=signal,
                    wireless_queue_delay_ms=queue_delay, **common,
                )
                baseline["sweep_signal_dbm"] = signal
                baseline["sweep_queue_delay_ms"] = queue_delay
                baseline["policy_classification"] = "baseline"
                adaptive["sweep_signal_dbm"] = signal
                adaptive["sweep_queue_delay_ms"] = queue_delay
                adaptive["policy_classification"] = classification
                detailed.extend((baseline, adaptive))
                paired_rows.extend((baseline, adaptive))

            _, report = paired_analysis(
                paired_rows, comparison_names=("adaptive_wireless",)
            )
            for item in report:
                item["signal_dbm"] = signal
                item["queue_delay_ms"] = queue_delay
                item["policy_classification"] = classification
                paired_reports.append(item)

            for scenario in ("baseline", "adaptive_wireless"):
                group = [row for row in detailed
                         if row["sweep_signal_dbm"] == signal
                         and row["sweep_queue_delay_ms"] == queue_delay
                         and row["scenario"] == scenario]
                successful = [row for row in group if row["delivery_success"]]
                summary: dict[str, Any] = {
                    "signal_dbm": signal,
                    "queue_delay_ms": queue_delay,
                    "policy_classification": classification if scenario == "adaptive_wireless" else "baseline",
                    "scenario": scenario,
                    "runs": len(group),
                    "successful_runs": len(successful),
                    "success_rate_pct": 100.0 * len(successful) / len(group) if group else 0.0,
                }
                for metric in metrics:
                    values = [float(row[metric]) for row in successful
                              if math.isfinite(float(row[metric]))]
                    summary[f"mean_{metric}"] = statistics.mean(values) if values else math.nan
                    summary[f"std_{metric}"] = statistics.stdev(values) if len(values) > 1 else 0.0 if values else math.nan
                summaries.append(summary)

    return detailed, summaries, paired_reports


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep adaptive TCP policy signal and queue-delay inputs.")
    parser.add_argument("--seeds", type=int, default=30)
    parser.add_argument("--start-seed", type=int, default=1)
    parser.add_argument("--packets", type=int, default=30)
    parser.add_argument("--signals", default="-79,-80,-81",
                        help="comma-separated signal levels in dBm")
    parser.add_argument("--queue-delays", default="39,40,41",
                        help="comma-separated queue delays in ms")
    parser.add_argument("--congestion-queue-threshold-ms", type=float, default=40.0)
    parser.add_argument("--weak-signal-threshold-db", type=float, default=-80.0)
    parser.add_argument("--good-to-bad", type=float, default=0.02)
    parser.add_argument("--bad-to-good", type=float, default=0.25)
    parser.add_argument("--good-loss", type=float, default=0.01)
    parser.add_argument("--bad-loss", type=float, default=0.80)
    parser.add_argument("--output-dir", type=Path, default=Path("results/sensitivity"))
    args = parser.parse_args()
    if args.seeds < 1 or args.packets < 1 or args.start_seed < 0:
        parser.error("--seeds and --packets must be >= 1; --start-seed must be >= 0")
    try:
        args.signals = parse_values(args.signals, "--signals")
        args.queue_delays = parse_values(args.queue_delays, "--queue-delays")
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
    if not math.isfinite(args.congestion_queue_threshold_ms) or args.congestion_queue_threshold_ms <= 0:
        parser.error("--congestion-queue-threshold-ms must be finite and > 0")
    if not math.isfinite(args.weak_signal_threshold_db):
        parser.error("--weak-signal-threshold-db must be finite")
    if any(value < 0 for value in args.queue_delays):
        parser.error("queue-delay values must be >= 0")
    for name in ("good_to_bad", "bad_to_good", "good_loss", "bad_loss"):
        value = getattr(args, name)
        if not math.isfinite(value) or not 0 <= value <= 1:
            parser.error(f"--{name.replace('_', '-')} must be between 0 and 1")

    detailed, summaries, reports = run_sweep(args)
    write_csv(args.output_dir / "sensitivity_detailed.csv", detailed)
    write_csv(args.output_dir / "sensitivity_summary.csv", summaries)
    write_csv(args.output_dir / "sensitivity_paired_report.csv", reports)
    print("=== Wireless TCP policy sensitivity sweep ===")
    print(f"Grid points: {len(args.signals)} signal levels x {len(args.queue_delays)} queue delays")
    print(f"Seeds per grid point: {args.seeds}; simulations: {len(detailed)}")
    print("\nPolicy classification grid (rows=queue delay; columns=signal strength):")
    print("queue_ms | " + " | ".join(f"{signal:g} dBm" for signal in args.signals))
    for queue_delay in args.queue_delays:
        classes = [classify_grid_point(signal, queue_delay,
                   args.congestion_queue_threshold_ms, args.weak_signal_threshold_db)
                   for signal in args.signals]
        print(f"{queue_delay:g} ms | " + " | ".join(classes))
    print(f"\nDetailed results: {args.output_dir / 'sensitivity_detailed.csv'}")
    print(f"Summary results: {args.output_dir / 'sensitivity_summary.csv'}")
    print(f"Paired statistics: {args.output_dir / 'sensitivity_paired_report.csv'}")
    print("Note: simulated inputs and shared time-indexed channel abstraction; not measured Wi-Fi telemetry.")


if __name__ == "__main__":
    main()
