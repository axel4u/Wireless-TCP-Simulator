# Wireless TCP Simulator

A Python discrete-event simulator for studying TCP behavior over unreliable wireless links. The project will compare a simplified TCP NewReno-style baseline with a conservative wireless-aware recovery policy.

> **Research boundary:** This is a discrete-event simulation, not a modified operating-system TCP stack or a standardized TCP implementation. Results must be measured; no performance improvement is claimed in advance.

## Current status — Milestone 2

Implemented:
- Deterministic discrete-event scheduler with cancellable events.
- DATA and ACK packet model.
- Wireless channel with configurable independent random packet loss and propagation delay.
- Receiver with out-of-order buffering and cumulative ACKs.
- Reliable stop-and-wait sender with retransmission timeout (RTO), retry limit, and cumulative ACK processing.
- Event log and automated tests.

Not implemented yet:
- TCP congestion window, NewReno, fast retransmit/recovery, wireless-aware loss classification, experiment runner, or dashboard.

## Requirements

- Python 3.10+
- Windows, macOS, or Linux

## Windows setup (PowerShell)

```powershell
git clone https://github.com/axel4u/Wireless-TCP-Simulator.git
cd Wireless-TCP-Simulator

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\python.exe -m pytest -q
```

Use the virtual-environment Python executable directly if PowerShell activation is restricted.

## Run experiments

Default run:

```powershell
.\.venv\Scripts\python.exe main.py
```

Higher loss:

```powershell
.\.venv\Scripts\python.exe main.py --packets 10 --loss 0.35 --delay-ms 25 --rto-ms 100 --seed 7
```

A run with total loss is expected to stop with a clear failure after the configured retry limit:

```powershell
.\.venv\Scripts\python.exe main.py --loss 1.0 --max-retransmissions 2
```

## Project layout

```text
simulator/
  event_scheduler.py
  packet.py
  channel.py
  receiver.py
  sender.py
tests/
main.py
```

## Planned milestones

1. Packet and channel foundation.
2. **Reliable delivery — current:** RTO-based retransmission and cumulative ACK handling.
3. TCP baseline — congestion window, slow start, congestion avoidance, fast retransmit/recovery.
4. Wireless-aware recovery — use explicit observable link signals; fall back to standard congestion response when evidence is uncertain or congestion is indicated.
5. Experiment runner — controlled scenarios, fixed seeds, metrics, repeated trials.
6. Streamlit + Plotly dashboard.
7. Validation, documentation, and optional comparison with an established network simulator if required.

## Experimental integrity

- Compare algorithms under identical channel settings and random seeds.
- Do not leak the simulator's hidden ground-truth loss cause into the policy.
- Treat congestion as real and preserve a conservative fallback.
- Report goodput, delay/RTT, retransmissions, recovery time, and fairness as appropriate.
- Document assumptions and limitations alongside every result.

## Current model limitation

The reliability sender uses a one-packet stop-and-wait window to isolate retransmission correctness. It is not yet TCP NewReno and does not model a congestion window. The RTO is fixed for now; adaptive RTT estimation will be considered in a later milestone.

## License

This repository currently has no license file.
