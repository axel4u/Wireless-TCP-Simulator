# Wireless TCP Simulator

A Python discrete-event simulator for studying TCP behavior over unreliable wireless links. It compares a simplified TCP NewReno baseline with a conservative wireless-aware timeout recovery policy.

> **Research boundary:** This is an educational discrete-event model, not a modified operating-system TCP stack or a complete standards-conformance implementation. Results must be measured; no performance improvement is claimed in advance.

## Current status — Milestone 5 (fair experiment foundation)

Implemented:
- Deterministic discrete-event scheduler with cancellable events.
- DATA and cumulative ACK packet model.
- Wireless channel with configurable independent random packet loss and propagation delay.
- Optional packet-keyed shared loss trace for repeatable cross-algorithm comparisons.
- Receiver with out-of-order buffering and cumulative ACK generation.
- Sliding-window sender with a single retransmission timer for the oldest unacknowledged packet.
- Congestion window (cwnd), slow start, congestion avoidance, duplicate ACK counting, fast retransmit, fast recovery, and timeout response.
- Initial rule-based adaptive timeout recovery using observable/simulated signal strength and queueing-delay inputs.
- Congestion-window history, event log, and automated tests.

The congestion window is expressed in packet/MSS units. The model uses a fixed RTO and does not yet model RTT estimation, delayed ACKs, receiver-advertised windows, packet queueing, burst-error channels, or all TCP NewReno edge cases.

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

## Fair comparison mode

Use `--loss-mode shared` in both runs. The shared trace keys each loss decision by packet direction, sequence number, and transmission-attempt number. Thus the same corresponding DATA/ACK attempt receives the same drop outcome in separate runs with the same seed and loss probability, regardless of transmission ordering.

Baseline:

~~~powershell
python main.py --packets 30 --loss 0.10 --loss-mode shared --seed 7
~~~

Adaptive wireless-aware run:

~~~powershell
python main.py --packets 30 --loss 0.10 --loss-mode shared --adaptive --signal-db -95 --queue-delay-ms 5 --seed 7
~~~

Adaptive congestion-fallback run:

~~~powershell
python main.py --packets 30 --loss 0.10 --loss-mode shared --adaptive --signal-db -95 --queue-delay-ms 80 --seed 7
~~~

The shared trace is deterministic and packet-keyed; it is not a time-varying physical channel model. Because ACK sequence numbers can be generated a different number of times by different sender behaviors, the comparison aligns corresponding attempts, not necessarily every event in chronological order. For stronger statistical claims, run multiple seeds and report averages and variability.

## Random mode

The default `--loss-mode random` retains the original sequential random-number generator behavior:

~~~powershell
python main.py --packets 30 --loss 0.10 --seed 7
~~~

## Adaptive policy assumptions

The adaptive inputs are explicit simulator measurements, not live Wi-Fi telemetry. The channel's hidden loss decision is not exposed to the policy. In this prototype, classification is applied to timeout recovery; duplicate-ACK fast recovery remains the conservative NewReno behavior. High queueing delay takes priority as congestion evidence; uncertain conditions use the standard timeout response.

## Project layout

~~~text
simulator/
  adaptive_policy.py
  channel.py
  congestion_control.py
  event_scheduler.py
  loss_trace.py
  packet.py
  receiver.py
  sender.py
tests/
  test_adaptive_policy.py
  test_adaptive_sender.py
  test_channel.py
  test_loss_trace.py
  test_sender.py
main.py
~~~

## Planned milestones

1. Packet and channel foundation — complete.
2. Reliable delivery with RTO and cumulative ACKs — complete.
3. TCP NewReno baseline — implemented.
4. Wireless-aware timeout recovery — initial policy implemented.
5. Shared-loss experiment foundation — implemented; repeated-seed statistics and additional metrics next.
6. Streamlit + Plotly dashboard.
7. Validation, documentation, and optional comparison with an established network simulator if required.

## Experimental integrity

- Use the shared packet-keyed loss mode for cross-algorithm comparisons.
- Run multiple seeds and report averages and variability before making performance claims.
- Do not leak the simulator's hidden ground-truth loss cause into the policy.
- Treat congestion as real and preserve a conservative fallback.
- Report goodput, delay/RTT, retransmissions, recovery time, and fairness as appropriate.
- Document assumptions and limitations alongside every result.

## License

This repository currently has no license file.
