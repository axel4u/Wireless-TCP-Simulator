"""Run repeatable multi-seed comparisons of baseline and adaptive recovery."""
from __future__ import annotations

import argparse
import csv
import math
import statistics
from pathlib import Path
from typing import Any

from simulator.adaptive_policy import AdaptiveRecoveryPolicy, LinkMetrics
from simulator.channel import WirelessChannel
from simulator.burst_loss import GilbertElliottLoss
from simulator.event_scheduler import EventScheduler
from simulator.loss_trace import SharedLossTrace
from simulator.paired_statistics import paired_analysis
from simulator.receiver import Receiver
from simulator.sender import Sender


SCENARIOS = ("baseline", "adaptive_wireless", "adaptive_congestion")


def run_one(
    scenario: str,
    seed: int,
    packets: int = 30,
    loss: float = 0.10,
    delay_ms: float = 25.0,
    rto_ms: float = 100.0,
    max_retransmissions: int = 20,
    signal_dbm: float = -95.0,
    wireless_queue_delay_ms: float = 5.0,
    congestion_queue_delay_ms: float = 80.0,
    loss_mode: str = "shared",
    channel_model: str = "independent",
) -> dict[str, Any]:
    """Run one scenario/seed and return a flat, CSV-friendly result row."""
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario: {scenario}")
    if loss_mode not in ("shared", "random"):
        raise ValueError("loss_mode must be 'shared' or 'random'")
    if channel_model not in ("independent", "burst"):
        raise ValueError("channel_model must be 'independent' or 'burst'")
    if channel_model == "burst" and loss_mode == "shared":
        raise ValueError("burst channel cannot use packet-keyed shared loss")

    scheduler = EventScheduler()
    trace = SharedLossTrace(loss, seed=seed) if loss_mode == "shared" else None
    burst_model = GilbertElliottLoss(seed=seed) if channel_model == "burst" else None
    channel = WirelessChannel(
        scheduler, loss_probability=loss, delay_ms=delay_ms,
        seed=seed, loss_trace=trace, burst_loss_model=burst_model,
    )
    receiver = Receiver(channel)

    policy = None
    queue_delay = ""
    if scenario == "adaptive_wireless":
        queue_delay = wireless_queue_delay_ms
        policy = AdaptiveRecoveryPolicy(
            LinkMetrics(signal_strength_dbm=signal_dbm,
                        queue_delay_ms=wireless_queue_delay_ms)
        )
    elif scenario == "adaptive_congestion":
        queue_delay = congestion_queue_delay_ms
        policy = AdaptiveRecoveryPolicy(
            LinkMetrics(signal_strength_dbm=signal_dbm,
                        queue_delay_ms=congestion_queue_delay_ms)
        )

    sender = Sender(
        channel, receiver, scheduler,
        retransmission_timeout_ms=rto_ms,
        max_retransmissions=max_retransmissions,
        adaptive_policy=policy,
    )
    error_message = ""
    sender.send_batch(packets)
    try:
        scheduler.run()
    except RuntimeError as error:
        error_message = str(error)

    completed = sender.is_complete and not sender.failed
    completion_ms = scheduler.now_ms if completed else math.nan
    goodput_mbps = (
        receiver.delivered_count * 1000 * 8 / (completion_ms * 1000)
        if completed and completion_ms > 0 else math.nan
    )
    return {
        "scenario": scenario,
        "seed": seed,
        "loss_mode": loss_mode,
        "channel_model": channel_model,
        "packets_configured": packets,
        "loss_probability": loss if channel_model == "independent" else "",
        "good_state_loss_probability": 0.01 if channel_model == "burst" else "",
        "bad_state_loss_probability": 0.80 if channel_model == "burst" else "",
        "good_to_bad_probability": 0.02 if channel_model == "burst" else "",
        "bad_to_good_probability": 0.25 if channel_model == "burst" else "",
        "signal_dbm": signal_dbm if policy is not None else "",
        "queue_delay_ms": queue_delay,
        "packets_delivered": receiver.delivered_count,
        "unique_packets_acked": sender.unique_acked_count,
        "delivery_success": completed,
        "completion_time_ms": completion_ms,
        "goodput_mbps": goodput_mbps,
        "retransmissions": sender.retransmission_count,
        "timeouts": sender.timeout_count,
        "packets_dropped": channel.dropped_count,
        "final_cwnd_packets": sender.cwnd_packets,
        "final_ssthresh_packets": sender.ssthresh_packets,
        "wireless_recoveries": sender.wireless_recovery_count,
        "congestion_recoveries": sender.congestion_recovery_count,
        "simulation_time_ms": scheduler.now_ms,
        "error": error_message,
    }


METRICS = (
    "completion_time_ms", "goodput_mbps", "retransmissions", "timeouts",
    "packets_dropped", "final_cwnd_packets", "final_ssthresh_packets",
)


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Summarize each scenario; performance means use successful runs only."""
    summaries: list[dict[str, Any]] = []
    for scenario in SCENARIOS:
        group = [row for row in rows if row["scenario"] == scenario]
        successful = [row for row in group if row["delivery_success"]]
        summary: dict[str, Any] = {
            "scenario": scenario,
            "runs": len(group),
            "successful_runs": len(successful),
            "delivery_success_rate_pct": (
                100.0 * len(successful) / len(group) if group else 0.0
            ),
        }
        for metric in METRICS:
            values = [float(row[metric]) for row in successful
                      if not math.isnan(float(row[metric]))]
            summary[f"mean_{metric}"] = statistics.mean(values) if values else math.nan
            summary[f"std_{metric}"] = (
                statistics.stdev(values) if len(values) > 1 else 0.0 if values else math.nan
            )
        summaries.append(summary)
    return summaries


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("cannot write an empty results file")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare NewReno and adaptive recovery across repeatable seeds."
    )
    parser.add_argument("--seeds", type=int, default=30,
                        help="number of seeds to run (default: 30)")
    parser.add_argument("--start-seed", type=int, default=1,
                        help="first seed in the consecutive seed range")
    parser.add_argument("--packets", type=int, default=30)
    parser.add_argument("--loss", type=float, default=0.10)
    parser.add_argument("--delay-ms", type=float, default=25.0)
    parser.add_argument("--rto-ms", type=float, default=100.0)
    parser.add_argument("--max-retransmissions", type=int, default=20)
    parser.add_argument("--loss-mode", choices=("shared", "random"), default="shared")
    parser.add_argument("--channel-model", choices=("independent", "burst"), default="independent")
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    args = parser.parse_args()
    if args.seeds < 1 or args.packets < 1:
        parser.error("--seeds and --packets must be >= 1")
    if args.start_seed < 0:
        parser.error("--start-seed must be >= 0")
    if not 0 <= args.loss <= 1:
        parser.error("--loss must be between 0 and 1")
    if args.delay_ms < 0 or args.rto_ms <= 0:
        parser.error("--delay-ms must be >= 0 and --rto-ms must be > 0")
    if args.max_retransmissions < 0:
        parser.error("--max-retransmissions must be >= 0")
    if args.channel_model == "burst" and args.loss_mode == "shared":
        parser.error("burst channel requires --loss-mode random")
    return args


def main() -> None:
    args = parse_args()
    rows: list[dict[str, Any]] = []
    for seed in range(args.start_seed, args.start_seed + args.seeds):
        for scenario in SCENARIOS:
            rows.append(run_one(
                scenario=scenario, seed=seed, packets=args.packets,
                loss=args.loss, delay_ms=args.delay_ms, rto_ms=args.rto_ms,
                max_retransmissions=args.max_retransmissions,
                loss_mode=args.loss_mode, channel_model=args.channel_model,
            ))

    summaries = summarize(rows)
    detailed_path = args.output_dir / "multi_seed_results.csv"
    summary_path = args.output_dir / "multi_seed_summary.csv"
    write_csv(detailed_path, rows)
    write_csv(summary_path, summaries)
    paired_path = args.output_dir / "paired_seed_comparisons.csv"
    statistical_path = args.output_dir / "paired_statistical_report.csv"
    statistical_report = []
    if args.channel_model == "independent":
        paired_rows, statistical_report = paired_analysis(rows)
        write_csv(paired_path, paired_rows)
        write_csv(statistical_path, statistical_report)
    else:
        paired_path.unlink(missing_ok=True)
        statistical_path.unlink(missing_ok=True)

    print("\n=== Multi-seed Wireless TCP Experiment ===")
    print(f"Seeds                 : {args.start_seed}..{args.start_seed + args.seeds - 1}")
    print(f"Runs                  : {len(rows)} ({args.seeds} seeds x {len(SCENARIOS)} scenarios)")
    print(f"Packets per run       : {args.packets}")
    if args.channel_model == "independent":
        print(f"Loss probability      : {args.loss:.1%}")
    else:
        print("Gilbert-Elliott rates : GOOD loss 1%, BAD loss 80%; GOOD->BAD 2%, BAD->GOOD 25%")
    print(f"Loss mode             : {args.loss_mode}")
    print(f"Channel model         : {args.channel_model}")
    print("\nScenario summary (mean ± sample standard deviation; successful runs):")
    for item in summaries:
        print(f"\n{item['scenario']} — success {item['successful_runs']}/{item['runs']} "
              f"({item['delivery_success_rate_pct']:.1f}%)")
        for metric in METRICS:
            mean = item[f"mean_{metric}"]
            std = item[f"std_{metric}"]
            if math.isnan(float(mean)):
                print(f"  {metric}: no successful observations")
            else:
                print(f"  {metric}: {mean:.3f} ± {std:.3f}")
    print(f"\nDetailed results : {detailed_path}")
    print(f"Summary results  : {summary_path}")
    if args.channel_model == "independent":
        print(f"\nPaired comparisons: {paired_path}")
        print(f"Statistical report: {statistical_path}")
        print("\nPaired comparison (delta = comparison minus baseline):")
    else:
        print("\nPaired statistical analysis: skipped (burst streams are not paired).")
    for item in statistical_report:
        if item["metric"] in ("completion_time_ms", "goodput_mbps", "timeouts"):
            print(
                f"  {item['comparison']} / {item['metric']}: "
                f"mean delta={item['mean_delta_comparison_minus_baseline']:.3f}, "
                f"95% CI=[{item['ci95_low_delta']:.3f}, {item['ci95_high_delta']:.3f}], "
                f"paired t p={item['paired_t_p_value_two_sided']:.6g}, "
                f"improved/equal/worsened={item['improved_seeds']}/"
                f"{item['equal_seeds']}/{item['worsened_seeds']}"
            )
    if args.channel_model == "burst":
        print("\nNote: burst-loss runs use independent seeded sequential streams per scenario. "
              "Compare scenario-level means, standard deviations, and success rates; "
              "do not interpret seed-matched differences as paired statistical evidence.")
    else:
        print("\nNote: packet-keyed shared loss aligns corresponding direction/sequence/attempt "
              "keys, not a fully time-aligned physical channel trace. Interpret results "
              "within the simulator's stated assumptions.")


if __name__ == "__main__":
    main()
