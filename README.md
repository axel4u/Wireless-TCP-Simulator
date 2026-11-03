# Wireless TCP Simulator

A Python discrete-event simulator for studying TCP behavior over unreliable wireless links. It is being developed to compare a simplified TCP NewReno baseline with a conservative wireless-aware recovery policy.

> **Research boundary:** This is an educational discrete-event model, not a modified operating-system TCP stack or a complete standards-conformance implementation. Results must be measured; no performance improvement is claimed in advance.

## Current status — Milestone 3

Implemented:
- Deterministic discrete-event scheduler with cancellable events.
- DATA and cumulative ACK packet model.
- Wireless channel with configurable independent random packet loss and propagation delay.
- Receiver with out-of-order buffering and cumulative ACK generation.
- Sliding-window sender with a single retransmission timer for the oldest unacknowledged packet.
- Congestion window (cwnd), slow start, congestion avoidance, duplicate ACK counting, fast retransmit, fast recovery, and timeout response.
- Congestion-window history, event log, and automated tests.

The congestion window is expressed in packet/MSS units to make the simulation easier to inspect. The current model uses a fixed RTO and independent random loss; it does not yet model RTT estimation, delayed ACKs, receiver-advertised windows, packet queueing, burst errors, or all TCP NewReno edge cases.

## Requirements

- Python 3.10+
- Windows, macOS, or Linux

## Windows setup

~~~powershell
git clone https://github.com/axel4u/Wireless-TCP-Simulator.git
cd Wireless-TCP-Simulator
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\python.exe -m pytest -q
~~~

In VS Code, select the project interpreter at .venv\\Scripts\\python.exe, configure pytest from the Testing panel, and use Source Control → Pull to receive updates.

## Run scenarios

Default wireless run:

~~~powershell
.\.venv\Scripts\python.exe main.py
~~~

Higher random loss:

~~~powershell
.\.venv\Scripts\python.exe main.py --packets 30 --loss 0.25 --delay-ms 25 --seed 7
~~~

Start with a larger initial window:

~~~powershell
.\.venv\Scripts\python.exe main.py --packets 30 --loss 0.0 --initial-cwnd 4 --ssthresh 12
~~~

A run with total loss is expected to stop with a clear failure after the configured retry limit:

~~~powershell
.\.venv\Scripts\python.exe main.py --loss 1.0 --max-retransmissions 2
~~~

## Project layout

~~~text
simulator/
  congestion_control.py
  event_scheduler.py
  packet.py
  channel.py
  receiver.py
  sender.py
tests/
  test_congestion_control.py
main.py
~~~

## Planned milestones

1. Packet and channel foundation — complete.
2. Reliable delivery with RTO and cumulative ACKs — complete.
3. **TCP NewReno baseline — implemented; local validation pending.**
4. Wireless-aware recovery — use observable link signals only; fall back to standard congestion response when evidence is uncertain or congestion is indicated.
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
