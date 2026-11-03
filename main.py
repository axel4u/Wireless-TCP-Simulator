"""Run the TCP NewReno wireless-link simulation."""
from __future__ import annotations

import argparse

from simulator.adaptive_policy import AdaptiveRecoveryPolicy, LinkMetrics
from simulator.channel import WirelessChannel
from simulator.event_scheduler import EventScheduler
from simulator.loss_trace import SharedLossTrace
from simulator.receiver import Receiver
from simulator.sender import Sender


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wireless TCP NewReno simulator")
    parser.add_argument("--packets", type=int, default=10, help="number of DATA packets")
    parser.add_argument("--loss", type=float, default=0.10, help="independent packet loss probability (0..1)")
    parser.add_argument("--delay-ms", type=float, default=25.0, help="one-way channel propagation delay")
    parser.add_argument("--rto-ms", type=float, default=100.0, help="retransmission timeout")
    parser.add_argument("--max-retransmissions", type=int, default=20, help="retry limit per packet")
    parser.add_argument("--seed", type=int, default=7, help="random seed")
    parser.add_argument(
        "--loss-mode", choices=("random", "shared"), default="random",
        help="random uses sequential RNG; shared uses packet-keyed outcomes comparable across runs",
    )
    parser.add_argument("--initial-cwnd", type=float, default=1.0, help="initial congestion window in packets")
    parser.add_argument("--ssthresh", type=float, default=8.0, help="initial slow-start threshold in packets")
    parser.add_argument("--adaptive", action="store_true", help="enable wireless-aware timeout recovery")
    parser.add_argument("--signal-db", type=float, default=-65.0, help="simulated signal strength in dBm")
    parser.add_argument("--queue-delay-ms", type=float, default=0.0, help="simulated queueing delay in ms")
    args = parser.parse_args()
    if args.packets < 1:
        parser.error("--packets must be >= 1")
    if not 0.0 <= args.loss <= 1.0:
        parser.error("--loss must be between 0 and 1")
    if args.delay_ms < 0 or args.rto_ms <= 0:
        parser.error("delay must be >= 0 and RTO must be > 0")
    if args.max_retransmissions < 0:
        parser.error("--max-retransmissions must be >= 0")
    if args.initial_cwnd < 1 or args.ssthresh < 2:
        parser.error("initial-cwnd must be >= 1 and ssthresh must be >= 2")
    return args


def main() -> None:
    args = parse_args()
    scheduler = EventScheduler()
    shared_trace = (
        SharedLossTrace(args.loss, seed=args.seed)
        if args.loss_mode == "shared"
        else None
    )
    channel = WirelessChannel(
        scheduler,
        loss_probability=args.loss,
        delay_ms=args.delay_ms,
        seed=args.seed,
        loss_trace=shared_trace,
    )
    receiver = Receiver(channel)
    adaptive_policy = None
    if args.adaptive:
        adaptive_policy = AdaptiveRecoveryPolicy(
            LinkMetrics(
                signal_strength_dbm=args.signal_db,
                queue_delay_ms=args.queue_delay_ms,
            )
        )
    sender = Sender(
        channel, receiver, scheduler,
        retransmission_timeout_ms=args.rto_ms,
        max_retransmissions=args.max_retransmissions,
        initial_cwnd_packets=args.initial_cwnd,
        initial_ssthresh_packets=args.ssthresh,
        adaptive_policy=adaptive_policy,
    )
    sender.send_batch(args.packets)
    try:
        scheduler.run()
    except RuntimeError as error:
        print(f"\nSIMULATION FAILED: {error}")
        raise SystemExit(1) from error

    mode = "wireless-aware adaptive" if args.adaptive else "TCP NewReno baseline"
    print(f"\n=== Wireless TCP Simulator: {mode} ===")
    print(f"Loss decision mode      : {args.loss_mode}")
    print(f"Configured DATA packets : {args.packets}")
    print(f"Channel loss probability: {args.loss:.1%}")
    print(f"One-way delay           : {args.delay_ms:.2f} ms")
    print(f"Retransmission timeout  : {args.rto_ms:.2f} ms")
    print(f"Initial cwnd            : {args.initial_cwnd:.2f} packets")
    print(f"Initial ssthresh        : {args.ssthresh:.2f} packets")
    print(f"DATA delivered          : {receiver.delivered_count}")
    print(f"Unique packets ACKed    : {sender.unique_acked_count}")
    print(f"Retransmissions         : {sender.retransmission_count}")
    print(f"Timeouts                : {sender.timeout_count}")
    print(f"Final cwnd              : {sender.cwnd_packets:.2f} packets")
    print(f"Final ssthresh          : {sender.ssthresh_packets:.2f} packets")
    print(f"Final congestion state  : {sender.congestion.state}")
    print(f"Delivery complete       : {'YES' if sender.is_complete else 'NO'}")
    print(f"Packets dropped         : {channel.dropped_count}")
    print(f"Virtual simulation time : {scheduler.now_ms:.2f} ms")
    if args.adaptive:
        print(f"Wireless recoveries     : {sender.wireless_recovery_count}")
        print(f"Congestion/fallback rec.: {sender.congestion_recovery_count}")
        print(f"Link signal strength    : {args.signal_db:.1f} dBm")
        print(f"Queueing delay input    : {args.queue_delay_ms:.2f} ms")
        print("Adaptive decisions      :")
        for time_ms, decision, trigger in sender.adaptive_decisions:
            print(f"  {time_ms:8.2f} ms | {trigger} -> {decision}")
    print("\nCongestion-window history (time_ms, cwnd_packets, state):")
    for time_ms, cwnd, state in sender.window_history:
        print(f"  {time_ms:8.2f} ms | cwnd={cwnd:6.2f} | {state}")
    print("\nEvent log:")
    for event in channel.events:
        print(f"  {event}")


if __name__ == "__main__":
    main()
