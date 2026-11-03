"""Run the reliable wireless packet simulation."""
from __future__ import annotations

import argparse

from simulator.channel import WirelessChannel
from simulator.event_scheduler import EventScheduler
from simulator.receiver import Receiver
from simulator.sender import Sender


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wireless TCP reliability simulator")
    parser.add_argument("--packets", type=int, default=10, help="number of DATA packets")
    parser.add_argument("--loss", type=float, default=0.10, help="independent packet loss probability (0..1)")
    parser.add_argument("--delay-ms", type=float, default=25.0, help="one-way channel propagation delay")
    parser.add_argument("--rto-ms", type=float, default=100.0, help="retransmission timeout")
    parser.add_argument("--max-retransmissions", type=int, default=20, help="retry limit per packet")
    parser.add_argument("--seed", type=int, default=7, help="random seed")
    args = parser.parse_args()
    if args.packets < 1:
        parser.error("--packets must be >= 1")
    if not 0.0 <= args.loss <= 1.0:
        parser.error("--loss must be between 0 and 1")
    if args.delay_ms < 0 or args.rto_ms <= 0:
        parser.error("delay must be >= 0 and RTO must be > 0")
    if args.max_retransmissions < 0:
        parser.error("--max-retransmissions must be >= 0")
    return args


def main() -> None:
    args = parse_args()
    scheduler = EventScheduler()
    channel = WirelessChannel(scheduler, loss_probability=args.loss,
                              delay_ms=args.delay_ms, seed=args.seed)
    receiver = Receiver(channel)
    sender = Sender(channel, receiver, scheduler,
                    retransmission_timeout_ms=args.rto_ms,
                    max_retransmissions=args.max_retransmissions)
    sender.send_batch(args.packets)
    try:
        scheduler.run()
    except RuntimeError as error:
        print(f"\nSIMULATION FAILED: {error}")
        raise SystemExit(1) from error

    print("\n=== Wireless TCP Simulator: Milestone 2 ===")
    print(f"Configured DATA packets : {args.packets}")
    print(f"Channel loss probability: {args.loss:.1%}")
    print(f"One-way delay           : {args.delay_ms:.2f} ms")
    print(f"Retransmission timeout  : {args.rto_ms:.2f} ms")
    print(f"Random seed             : {args.seed}")
    print(f"DATA delivered          : {receiver.delivered_count}")
    print(f"Unique packets ACKed    : {sender.unique_acked_count}")
    print(f"Retransmissions         : {sender.retransmission_count}")
    print(f"Timeouts                : {sender.timeout_count}")
    print(f"Delivery complete       : {'YES' if sender.is_complete else 'NO'}")
    print(f"Packets dropped         : {channel.dropped_count}")
    print(f"Virtual simulation time : {scheduler.now_ms:.2f} ms")
    print("\nEvent log:")
    for event in channel.events:
        print(f"  {event}")


if __name__ == "__main__":
    main()
