# Wireless TCP Simulator

A Python discrete-event simulator for studying TCP behavior over unreliable wireless links. It compares a simplified TCP NewReno baseline with a conservative wireless-aware timeout recovery policy.

> **Research boundary:** This is an educational discrete-event model, not a modified operating-system TCP stack or a complete standards-conformance implementation. Results must be measured; no performance improvement is claimed in advance.

## Current status — Milestone 6.1 (paired statistical evaluation)

Implemented:
- Deterministic discrete-event scheduler with cancellable events.
- DATA and cumulative ACK packet model.
- Wireless channel with configurable independent random packet loss and propagation delay.
- Optional packet-keyed shared loss trace for repeatable cross-algorithm comparisons.
- Multi-seed experiment runner with per-seed paired comparisons, confidence intervals, paired t-tests, and exact sign tests.
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
  paired_statistics.py
  packet.py
  receiver.py
  sender.py
tests/
  test_adaptive_policy.py
  test_adaptive_sender.py
  test_channel.py
  test_loss_trace.py
  test_paired_statistics.py
  test_sender.py
main.py
~~~

## Multi-seed experimental evaluation

The experiment runner executes the baseline, adaptive wireless, and adaptive congestion-fallback scenarios across a consecutive range of seeds. It uses shared packet-keyed loss by default and writes one detailed CSV row per scenario/seed plus a summary CSV.

Run the recommended 30-seed evaluation from the repository root:

~~~powershell
python run_experiments.py
~~~

Useful options:

~~~powershell
python run_experiments.py --seeds 50 --start-seed 1 --packets 30 --loss 0.10
python run_experiments.py --seeds 10 --start-seed 100 --loss-mode random
python run_experiments.py --seeds 30 --output-dir results/low-loss --loss 0.05
~~~

Output files (created automatically):

- `results/multi_seed_results.csv` — detailed result for every scenario and seed.
- `results/multi_seed_summary.csv` — per-scenario delivery success rate, mean, and sample standard deviation.
- `results/paired_seed_comparisons.csv` — baseline and comparison metrics plus per-seed deltas.
- `results/paired_statistical_report.csv` — paired mean/median deltas, 95% confidence intervals, paired t-test p-values, and exact two-sided sign-test p-values.

Metrics include delivered packets, unique ACKs, completion time, goodput, retransmissions, timeouts, drops, final cwnd/ssthresh, and recovery-decision counts. Goodput is calculated as successfully delivered application payload bits divided by elapsed simulation time. Means and standard deviations for performance metrics use successful runs; delivery success rate is reported separately. Failed runs remain visible in the detailed CSV with an error message.

The default scenarios use -95 dBm with 5 ms queue delay for the wireless-aware case, and -95 dBm with 80 ms queue delay for congestion fallback. These are controlled simulated inputs, not live telemetry.

### Paired statistical analysis

The runner matches baseline and comparison runs by seed. It writes one paired row per seed and comparison, with each delta defined as comparison minus baseline. Performance comparisons use only matched seeds where both runs completed successfully; the number of matched successful pairs is recorded. Completion time, retransmissions, timeouts, and packet drops treat a negative delta as favorable; goodput treats a positive delta as favorable. Congestion-window and threshold deltas are descriptive and are not labeled as universally better or worse.

The report includes a two-sided paired t-test and 95% t-based confidence interval for the mean paired difference, plus a two-sided exact sign test that counts non-tied wins and losses. These calculations use the Python standard library; no extra statistical package is required. The sign test is a useful distribution-light cross-check, while the paired t-test and confidence interval rely on the usual assumptions about independent seed-level pairs and the sampling distribution of their mean. The shared trace is packet-keyed rather than fully time-aligned, so statistical significance does not remove the simulator's modeling limitations. Do not interpret a p-value as proof of real-world network performance.

**Interpretation:** the shared loss trace aligns corresponding direction/sequence/attempt keys; it is not a fully time-aligned physical channel trace. Treat the output as evidence within this simulator's assumptions, not as proof of real-network performance. Report the seed range, configuration, success rate, means, and variability.

## Planned milestones

1. Packet and channel foundation — complete.
2. Reliable delivery with RTO and cumulative ACKs — complete.
3. TCP NewReno baseline — implemented.
4. Wireless-aware timeout recovery — initial policy implemented.
5. Shared-loss experiment foundation — implemented.
6. Multi-seed experimental evaluation and CSV reporting — implemented.
6.1 Paired per-seed statistical evaluation — implemented.
7. Streamlit + Plotly dashboard.
8. Validation, documentation, and optional comparison with an established network simulator if required.

## Experimental integrity

- Use the shared packet-keyed loss mode for cross-algorithm comparisons.
- Run multiple seeds and report averages and variability before making performance claims.
- Do not leak the simulator's hidden ground-truth loss cause into the policy.
- Treat congestion as real and preserve a conservative fallback.
- Report goodput, delay/RTT, retransmissions, recovery time, and fairness as appropriate.
- Document assumptions and limitations alongside every result.

## License

This repository currently has no license file.
