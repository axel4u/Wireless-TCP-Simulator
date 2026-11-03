# Wireless TCP Simulator

A Python-based educational simulator for studying TCP behavior over unreliable wireless links. The project will compare a simplified TCP NewReno-style baseline with a conservative wireless-aware recovery policy.

> **Research boundary:** This is a discrete-event simulation, not a modified operating-system TCP stack or a standardized TCP implementation. Results must be measured; no performance improvement is claimed in advance.

## Current status — Milestone 1

Implemented:
- Deterministic discrete-event scheduler (virtual time; stable event ordering).
- DATA and ACK packet model.
- Wireless channel with configurable independent packet loss and propagation delay.
- Receiver with out-of-order buffering and cumulative ACKs.
- Fixed-batch sender and event log.
- Unit tests.

Not implemented yet:
- Retransmission timeout (RTO), retransmissions, congestion window, NewReno, wireless-aware classification, experiments, or dashboard.

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

Using the virtual-environment Python executable directly avoids PowerShell activation-policy issues.

## Run

```powershell
python main.py
```

Optional arguments:

```powershell
python main.py --packets 20 --loss 0.10 --delay-ms 25 --seed 7
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

1. **Packet and channel foundation** — current.
2. Reliable delivery — retransmission timers, timeout handling, duplicate ACK tracking.
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

## License

This repository currently has no license file.