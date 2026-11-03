"""Interactive Streamlit dashboard for the Wireless TCP Simulator."""
from __future__ import annotations

import math
import re

import plotly.graph_objects as go

import pandas as pd
import plotly.express as px
import streamlit as st

from simulator.adaptive_policy import AdaptiveRecoveryPolicy, LinkMetrics
from simulator.burst_loss import GilbertElliottLoss
from simulator.shared_burst_trace import SharedBurstLossTrace
from simulator.channel import WirelessChannel
from simulator.event_scheduler import EventScheduler
from simulator.loss_trace import SharedLossTrace
from simulator.receiver import Receiver
from simulator.sender import Sender


SCENARIOS = {
    "NewReno baseline": "baseline",
    "Adaptive — wireless conditions": "adaptive_wireless",
    "Adaptive — congestion conditions": "adaptive_congestion",
}


def run_simulation(
    scenario: str,
    *,
    packets: int,
    loss: float,
    delay_ms: float,
    rto_ms: float,
    seed: int,
    signal_dbm: float,
    queue_delay_ms: float,
    loss_mode: str = "shared",
    channel_model: str = "independent",
    good_to_bad_probability: float = 0.02,
    bad_to_good_probability: float = 0.25,
    good_state_loss_probability: float = 0.01,
    bad_state_loss_probability: float = 0.80,
    burst_trace_mode: str = "shared-time",
) -> dict:
    """Run one simulation and return metrics plus time-series data."""
    scheduler = EventScheduler()
    trace = SharedLossTrace(loss, seed=seed) if loss_mode == "shared" else None
    burst_model = GilbertElliottLoss(
        good_to_bad_probability=good_to_bad_probability,
        bad_to_good_probability=bad_to_good_probability,
        good_state_loss_probability=good_state_loss_probability,
        bad_state_loss_probability=bad_state_loss_probability,
        seed=seed,
    ) if channel_model == "burst" and burst_trace_mode == "sequential" else None
    shared_burst_trace = SharedBurstLossTrace(
        good_to_bad_probability=good_to_bad_probability,
        bad_to_good_probability=bad_to_good_probability,
        good_state_loss_probability=good_state_loss_probability,
        bad_state_loss_probability=bad_state_loss_probability,
        seed=seed,
    ) if channel_model == "burst" and burst_trace_mode == "shared-time" else None
    burst_stats = shared_burst_trace or burst_model
    channel = WirelessChannel(
        scheduler,
        loss_probability=loss,
        delay_ms=delay_ms,
        seed=seed,
        loss_trace=trace,
        burst_loss_model=burst_model,
        shared_burst_trace=shared_burst_trace,
    )
    receiver = Receiver(channel)

    policy = None
    if scenario != "baseline":
        policy = AdaptiveRecoveryPolicy(
            LinkMetrics(
                signal_strength_dbm=signal_dbm,
                queue_delay_ms=queue_delay_ms,
            )
        )

    sender = Sender(
        channel,
        receiver,
        scheduler,
        retransmission_timeout_ms=rto_ms,
        adaptive_policy=policy,
    )
    sender.send_batch(packets)
    error = ""
    try:
        scheduler.run()
    except RuntimeError as exc:
        error = str(exc)

    completed = sender.is_complete and not sender.failed and not error
    elapsed_ms = scheduler.now_ms if completed else math.nan
    goodput_mbps = (
        receiver.delivered_count * 1000 * 8 / (elapsed_ms * 1000)
        if completed and elapsed_ms > 0
        else math.nan
    )

    return {
        "scenario": scenario,
        "packets_configured": packets,
        "packets_delivered": receiver.delivered_count,
        "unique_packets_acked": sender.unique_acked_count,
        "delivery_success": completed,
        "completion_time_ms": elapsed_ms,
        "goodput_mbps": goodput_mbps,
        "retransmissions": sender.retransmission_count,
        "timeouts": sender.timeout_count,
        "packets_dropped": channel.dropped_count,
        "transmission_attempts": channel.sent_count,
        "measured_loss_rate_pct": 100.0 * channel.dropped_count / channel.sent_count if channel.sent_count else 0.0,
        "good_state_occupancy_pct": 100.0 * burst_stats.good_state_attempts / burst_stats.attempt_count if burst_stats and burst_stats.attempt_count else None,
        "bad_state_occupancy_pct": 100.0 * burst_stats.bad_state_attempts / burst_stats.attempt_count if burst_stats and burst_stats.attempt_count else None,
        "final_cwnd_packets": sender.cwnd_packets,
        "final_ssthresh_packets": sender.ssthresh_packets,
        "wireless_recoveries": sender.wireless_recovery_count,
        "congestion_recoveries": sender.congestion_recovery_count,
        "window_history": sender.window_history,
        "adaptive_decisions": sender.adaptive_decisions,
        "channel_events": channel.events,
        "channel_transmission_records": channel.transmission_records,
        "error": error,
    }


def make_window_chart(history: list[tuple[float, float, str]], title: str):
    frame = pd.DataFrame(
        history, columns=["Time (ms)", "Congestion window (packets)", "TCP state"]
    )
    figure = px.line(
        frame,
        x="Time (ms)",
        y="Congestion window (packets)",
        color="TCP state",
        markers=True,
        title=title,
    )
    figure.update_layout(
        template="plotly_dark", paper_bgcolor="#101923", plot_bgcolor="#101923",
        font={"family":"Inter, Segoe UI, sans-serif","color":"#dce5ed"},
        legend_title_text="TCP state", hovermode="x unified",
        margin={"l":18,"r":18,"t":55,"b":35},
    )
    figure.update_xaxes(gridcolor="#263544")
    figure.update_yaxes(gridcolor="#263544")
    return figure



def make_packet_animation(events: list[str]):
    """Build a step-by-step packet journey from the channel's recorded events."""
    pattern = re.compile(
        r"^\s*([0-9.]+) ms \| (DATA|ACK) seq=(\d+) (SENT|DROPPED|DELIVERED)$"
    )
    parsed = []
    for raw in events:
        match = pattern.match(raw)
        if not match:
            continue
        time_ms, packet_type, sequence, action = match.groups()
        if action == "SENT":
            x, status = 1, "Entered wireless channel"
        elif action == "DROPPED":
            x, status = 1, "Dropped by wireless channel"
        else:
            x = 2 if packet_type == "DATA" else 0
            status = "Arrived at receiver" if packet_type == "DATA" else "ACK arrived at sender"
        parsed.append({
            "time_ms": float(time_ms),
            "packet_type": packet_type,
            "sequence": int(sequence),
            "action": action,
            "x": x,
            "status": status,
            "label": f"{packet_type} #{sequence}",
        })

    if not parsed:
        return None, pd.DataFrame()

    frames = []
    for index, event in enumerate(parsed):
        frames.append(go.Frame(
            name=str(index),
            data=[go.Scatter(
                x=[event["x"]], y=[0], mode="markers+text",
                marker={"size": 25, "symbol": "x" if event["action"] == "DROPPED" else "circle"},
                text=[event["label"]], textposition="top center",
                hovertemplate=(
                    f"{event['label']}<br>{event['status']}<br>"
                    f"Time: {event['time_ms']:.2f} ms<extra></extra>"
                ),
            )],
            layout=go.Layout(title_text=(
                f"Step {index + 1}/{len(parsed)} · {event['label']} · "
                f"{event['status']} · {event['time_ms']:.2f} ms"
            )),
        ))

    first = parsed[0]
    figure = go.Figure(
        data=[go.Scatter(
            x=[first["x"]], y=[0], mode="markers+text",
            marker={"size": 25, "symbol": "x" if first["action"] == "DROPPED" else "circle"},
            text=[first["label"]], textposition="top center",
        )],
        frames=frames,
    )
    figure.add_annotation(
        x=2, y=0.48, ax=0, ay=0.48,
        xref="x", yref="y", axref="x", ayref="y",
        text="DATA direction", showarrow=True, arrowhead=3,
        arrowsize=1.2, arrowwidth=2.5, arrowcolor="#4DA3FF",
        font={"color": "#4DA3FF", "size": 13},
        yshift=4,
    )
    figure.add_annotation(
        x=0, y=-0.48, ax=2, ay=-0.48,
        xref="x", yref="y", axref="x", ayref="y",
        text="ACK direction", showarrow=True, arrowhead=3,
        arrowsize=1.2, arrowwidth=2.5, arrowcolor="#FFB86B",
        font={"color": "#FFB86B", "size": 13},
        yshift=-4,
    )
    figure.update_layout(
        template="plotly_dark", paper_bgcolor="#101923", plot_bgcolor="#101923",
        font={"family":"Inter, Segoe UI, sans-serif","color":"#dce5ed"},
        title=f"Packet journey · {len(parsed)} channel events",
        xaxis={
            "range": [-0.35, 2.35], "tickmode": "array",
            "tickvals": [0, 1, 2],
            "ticktext": ["Sender", "Wireless channel", "Receiver"],
            "fixedrange": True,
        },
        yaxis={"range": [-0.85, 0.85], "visible": False, "fixedrange": True},
        height=390,
        showlegend=False,
        updatemenus=[{
            "type": "buttons", "showactive": False, "x": 0.05, "y": -0.18,
            "buttons": [
                {"label": "Play", "method": "animate",
                 "args": [None, {"frame": {"duration": 1200, "redraw": True},
                                 "transition": {"duration": 300},
                                 "fromcurrent": True}]},
                {"label": "Pause", "method": "animate",
                 "args": [[None], {"mode": "immediate", "frame": {"duration": 0},
                                   "transition": {"duration": 0}}]},
            ],
        }],
        sliders=[{
            "active": 0, "y": -0.05, "x": 0.15, "len": 0.82,
            "steps": [{
                "label": str(i + 1), "method": "animate",
                "args": [[str(i)], {"mode": "immediate",
                                    "frame": {"duration": 0, "redraw": True},
                                    "transition": {"duration": 0}}],
            } for i in range(len(parsed))],
        }],
        margin={"b": 100},
    )
    event_frame = pd.DataFrame(parsed)
    return figure, event_frame



st.set_page_config(
    page_title="Wireless TCP Simulator",
    layout="wide",
)


st.markdown(
    """
    <style>
    :root { --app-bg:#0b1017; --panel:#111a24; --line:#263544; --text:#edf2f7; --muted:#9aabba; --accent:#43b7a5; }
    .stApp { background:var(--app-bg); color:var(--text); }
    [data-testid="stHeader"] { background:rgba(11,16,23,.94); }
    [data-testid="stSidebar"] { background:#0e151e; border-right:1px solid var(--line); }
    [data-testid="stSidebar"] > div { padding-top:1.5rem; }
    .block-container { max-width:1440px; padding-top:2rem; padding-bottom:3rem; }
    h1,h2,h3 { color:var(--text)!important; letter-spacing:-.025em; }
    h1 { font-size:2.15rem!important; font-weight:650!important; }
    h2 { font-size:1.35rem!important; font-weight:620!important; margin-top:1.5rem!important; }
    h3 { font-size:1.05rem!important; font-weight:600!important; }
    [data-testid="stCaptionContainer"],.stCaption { color:var(--muted)!important; }
    [data-testid="stMetric"] { background:linear-gradient(145deg,#14212c,#101923); border:1px solid var(--line); border-radius:12px; padding:16px 18px; min-height:112px; }
    [data-testid="stMetricLabel"] p { color:var(--muted)!important; font-size:.82rem!important; font-weight:550; }
    [data-testid="stMetricValue"] { color:var(--text)!important; font-weight:650; }
    div[data-testid="stDataFrame"],div[data-testid="stPlotlyChart"] { border:1px solid var(--line); border-radius:12px; overflow:hidden; background:#101923; }
    .stButton>button { border-radius:8px; border:1px solid #3b9f94; background:#238b80; color:white; font-weight:600; min-height:2.7rem; }
    .stButton>button:hover { background:#2a9d90; border-color:#55c7b6; color:white; }
    [data-baseweb="select"]>div,[data-baseweb="input"]>div { background:#111b26; border-color:#304253; border-radius:8px; }
    hr { border-color:var(--line)!important; }
    .dashboard-kicker {
        display:inline-block;
        color:#75e0d0 !important;
        font-size:.78rem;
        font-weight:750;
        letter-spacing:.16em;
        line-height:1.5;
        text-transform:uppercase;
        opacity:1 !important;
        margin:0 0 .7rem 0;
        text-shadow:0 0 1px rgba(117,224,208,.25);
    }
    .dashboard-subtitle { color:var(--muted); font-size:1rem; max-width:850px; line-height:1.6; margin-top:-.3rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


st.markdown('<div class="dashboard-kicker">NETWORK PERFORMANCE LAB</div>', unsafe_allow_html=True)
st.title("Wireless TCP Simulator")
st.markdown(
    '<div class="dashboard-subtitle">Evaluate a NewReno-style baseline against '
    'a rule-based wireless-aware timeout recovery policy under controlled '
    'packet-loss and channel conditions.</div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Experiment setup")
    st.caption("Configure network conditions and recovery inputs.")
    packets = st.slider("DATA packets", min_value=5, max_value=100, value=30, step=5)
    channel_model = st.selectbox(
        "Wireless channel model",
        options=["independent", "burst"],
        format_func=lambda value: "Independent random loss" if value == "independent" else "Burst loss (Gilbert–Elliott)",
    )
    loss = st.slider(
        "Packet loss probability (independent mode)", min_value=0.0, max_value=0.50,
        value=0.10, step=0.01, format="%.2f",
        disabled=channel_model == "burst",
    )
    if channel_model == "burst":
        burst_trace_mode = st.selectbox(
            "Burst trace mode",
            options=["shared-time", "sequential"],
            format_func=lambda value: "Shared time-indexed trace (recommended)" if value == "shared-time" else "Sequential per-run stream",
        )
        st.subheader("Gilbert–Elliott parameters")
        good_loss = st.slider("GOOD-state loss", 0.0, 1.0, 0.01, 0.01)
        bad_loss = st.slider("BAD-state loss", 0.0, 1.0, 0.80, 0.01)
        good_to_bad = st.slider("GOOD → BAD transition", 0.0, 1.0, 0.02, 0.01)
        bad_to_good = st.slider("BAD → GOOD transition", 0.0, 1.0, 0.25, 0.01)
    else:
        burst_trace_mode = "shared-time"
        good_loss, bad_loss, good_to_bad, bad_to_good = 0.01, 0.80, 0.02, 0.25
    delay_ms = st.slider(
        "One-way propagation delay (ms)", 0.0, 200.0, 25.0, 5.0
    )
    rto_ms = st.slider(
        "Retransmission timeout (ms)", 20.0, 500.0, 100.0, 10.0
    )
    seed = st.number_input("Random seed", min_value=0, max_value=1_000_000, value=7)
    st.divider()
    st.subheader("Simulated link measurements")
    signal_dbm = st.slider(
        "Signal strength (dBm)", min_value=-110, max_value=-30, value=-95, step=1
    )
    queue_delay_ms = st.slider(
        "Queueing delay (ms)", min_value=0, max_value=150, value=5, step=1
    )
    st.caption(
        "These are controlled simulator inputs, not measurements from your "
        "computer's Wi-Fi adapter."
    )
    run_button = st.button("Run comparison", type="primary", width="stretch")

with st.expander("Channel model and comparison method", expanded=False):
    st.markdown(
        """
        - **Independent loss:** scenarios use shared packet-keyed loss outcomes.
        - **Burst loss:** a seeded Gilbert–Elliott model controls GOOD/BAD channel states.
        - **Shared-time trace:** scenarios use the same deterministic channel-state
          timeline at each virtual-time slot.

        These are simulated channel conditions, not live measurements from a Wi-Fi adapter.
        """
    )

if run_button:
    with st.spinner("Running three simulations..."):
        results = {}
        for label, scenario in SCENARIOS.items():
            effective_queue = queue_delay_ms
            if scenario == "adaptive_congestion":
                # Keep this scenario as an explicit congestion-evidence control.
                effective_queue = max(float(queue_delay_ms), 40.0)
            results[label] = run_simulation(
                scenario,
                packets=packets,
                loss=loss,
                delay_ms=delay_ms,
                rto_ms=rto_ms,
                seed=int(seed),
                signal_dbm=float(signal_dbm),
                queue_delay_ms=float(effective_queue),
                loss_mode="random" if channel_model == "burst" else "shared",
                channel_model=channel_model,
                good_to_bad_probability=good_to_bad,
                bad_to_good_probability=bad_to_good,
                good_state_loss_probability=good_loss,
                bad_state_loss_probability=bad_loss,
                burst_trace_mode=burst_trace_mode,
            )
        st.session_state["wireless_tcp_results"] = results
        st.session_state["wireless_tcp_config"] = {
            "packets": packets,
            "loss": loss,
            "delay_ms": delay_ms,
            "rto_ms": rto_ms,
            "seed": int(seed),
            "signal_dbm": signal_dbm,
            "queue_delay_ms": queue_delay_ms,
            "channel_model": channel_model,
            "good_loss": good_loss,
            "bad_loss": bad_loss,
            "good_to_bad": good_to_bad,
            "bad_to_good": bad_to_good,
            "burst_trace_mode": burst_trace_mode,
        }

results = st.session_state.get("wireless_tcp_results")
config = st.session_state.get("wireless_tcp_config")

if not results:
    st.subheader("How to use the dashboard")
    st.markdown(
        """
        1. Adjust the simulation settings in the sidebar.
        2. Set signal strength and queueing delay to represent the link
           conditions you want to study.
        3. Select **Run simulation comparison**.
        4. Compare delivery, goodput, retransmissions, timeouts and congestion
           window behaviour across the three scenarios.
        """
    )
    st.subheader("Recovery policy")
    st.markdown(
        """
        - **Likely wireless:** weak signal and queue delay below the congestion
          threshold; retransmit without reducing the congestion window.
        - **Likely congestion:** queue delay at or above 40 ms; use the
          conservative NewReno-style timeout response.
        - **Uncertain:** use the conservative NewReno-style timeout response.
        """
    )
else:
    st.subheader("Performance overview")
    channel_caption = (
        f"GOOD loss {config['good_loss']:.0%}, BAD loss {config['bad_loss']:.0%}; "
        f"GOOD→BAD {config['good_to_bad']:.0%}, BAD→GOOD {config['bad_to_good']:.0%}"
        if config["channel_model"] == "burst" else f"{config['loss']:.0%} independent loss"
    )
    st.caption(
        f"{config['packets']} packets · {channel_caption} · "
        f"{config['delay_ms']:.0f} ms one-way delay · seed {config['seed']}"
    )

    summary_rows = []
    for label, result in results.items():
        summary_rows.append(
            {
                "Scenario": label,
                "Delivery": (
                    f"{result['packets_delivered']}/{result['packets_configured']}"
                    if result["delivery_success"]
                    else f"Failed ({result['packets_delivered']}/{result['packets_configured']})"
                ),
                "Completion (ms)": result["completion_time_ms"],
                "Goodput (Mbps)": result["goodput_mbps"],
                "Retransmissions": result["retransmissions"],
                "Timeouts": result["timeouts"],
                "Dropped": result["packets_dropped"],
            }
        )
    summary = pd.DataFrame(summary_rows)

    baseline = results["NewReno baseline"]
    adaptive = results["Adaptive — wireless conditions"]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Adaptive completion time",
        f"{adaptive['completion_time_ms']:.1f} ms"
        if adaptive["delivery_success"] else "Failed",
        f"{baseline['completion_time_ms'] - adaptive['completion_time_ms']:.1f} ms vs baseline"
        if adaptive["delivery_success"] and baseline["delivery_success"] else None,
    )
    col2.metric(
        "Adaptive goodput",
        f"{adaptive['goodput_mbps']:.3f} Mbps"
        if adaptive["delivery_success"] else "Unavailable",
        f"{adaptive['goodput_mbps'] - baseline['goodput_mbps']:+.3f} Mbps vs baseline"
        if adaptive["delivery_success"] and baseline["delivery_success"] else None,
    )
    col3.metric("Adaptive retransmissions", adaptive["retransmissions"])
    col4.metric("Adaptive timeouts", adaptive["timeouts"])

    st.dataframe(
        summary,
        hide_index=True,
        width="stretch",
        column_config={
            "Scenario": st.column_config.TextColumn("Scenario", width="large"),
            "Delivery": st.column_config.TextColumn("Delivered", width="small"),
            "Completion (ms)": st.column_config.NumberColumn("Completion", format="%.1f ms"),
            "Goodput (Mbps)": st.column_config.NumberColumn("Goodput", format="%.3f Mbps"),
            "Retransmissions": st.column_config.NumberColumn("Retrans.", format="%d"),
            "Timeouts": st.column_config.NumberColumn("Timeouts", format="%d"),
            "Dropped": st.column_config.NumberColumn("Dropped", format="%d"),
        },
    )
    with st.expander("Additional channel and congestion metrics"):
        detail_rows = []
        for label, result in results.items():
            detail_rows.append({
                "Scenario": label,
                "Measured loss (%)": result["measured_loss_rate_pct"],
                "GOOD-state share (%)": result["good_state_occupancy_pct"],
                "BAD-state share (%)": result["bad_state_occupancy_pct"],
                "Final cwnd (packets)": result["final_cwnd_packets"],
                "Final ssthresh (packets)": result["final_ssthresh_packets"],
                "Wireless recoveries": result["wireless_recoveries"],
                "Congestion recoveries": result["congestion_recoveries"],
            })
        st.dataframe(pd.DataFrame(detail_rows), hide_index=True, width="stretch")

    left, right = st.columns(2)
    with left:
        figure = px.bar(
            summary,
            x="Scenario",
            y="Completion (ms)",
            color="Scenario",
            title="Completion time · lower is better",
        )
        st.plotly_chart(figure, width="stretch")
    with right:
        figure = px.bar(
            summary,
            x="Scenario",
            y="Goodput (Mbps)",
            color="Scenario",
            title="Goodput · higher is better",
        )
        st.plotly_chart(figure, width="stretch")


    st.subheader("Channel transmission records")
    st.caption("Each row records virtual time, packet direction, sequence, attempt, channel state and loss decision.")
    trace_label = st.selectbox("Choose channel trace", list(SCENARIOS), key="channel_trace_scenario")
    trace_records = results[trace_label]["channel_transmission_records"]
    if trace_records:
        st.dataframe(pd.DataFrame(trace_records), hide_index=True, width="stretch")

    st.subheader("Packet-flow playback")
    st.caption(
        "Play the recorded channel events step by step. DATA travels sender → "
        "wireless channel → receiver; ACK travels in the reverse direction. "
        "A dropped marker shows a packet lost at the channel."
    )
    animation_label = st.selectbox(
        "Choose packet-flow scenario", list(SCENARIOS), key="packet_animation_scenario"
    )
    animation_result = results[animation_label]
    packet_figure, packet_events = make_packet_animation(
        animation_result["channel_events"]
    )
    if packet_figure is not None:
        st.plotly_chart(packet_figure, width="stretch")
        display_events = packet_events[
            ["time_ms", "packet_type", "sequence", "action", "status"]
        ].rename(columns={
            "time_ms": "Time (ms)", "packet_type": "Packet",
            "sequence": "Sequence", "action": "Channel event", "status": "Meaning",
        })
        with st.expander("View complete packet event log"):
            st.dataframe(display_events, hide_index=True, width="stretch")
    else:
        st.info("No channel events were recorded for this run.")

    st.subheader("Congestion-window dynamics")
    selected_label = st.selectbox("Choose a scenario trace", list(SCENARIOS))
    selected_result = results[selected_label]
    st.plotly_chart(
        make_window_chart(
            selected_result["window_history"],
            f"{selected_label}: congestion window over simulation time",
        ),
        width="stretch",
    )

    st.subheader("Recovery decision log")
    decision_rows = []
    for label, result in results.items():
        for time_ms, decision, trigger in result["adaptive_decisions"]:
            decision_rows.append(
                {
                    "Scenario": label,
                    "Time (ms)": time_ms,
                    "Trigger": trigger,
                    "Classification": decision,
                }
            )
    if decision_rows:
        st.dataframe(pd.DataFrame(decision_rows), hide_index=True, width="stretch")
    else:
        st.write("No adaptive timeout decisions occurred in these runs.")

    selected_queue = (
        max(float(config["queue_delay_ms"]), 40.0)
        if selected_label == "Adaptive — congestion conditions"
        else float(config["queue_delay_ms"])
    )
    if selected_label == "NewReno baseline":
        st.info("Baseline mode: standard NewReno-style timeout recovery is used.")
    elif selected_queue >= 40.0:
        st.warning(
            "The queue-delay input meets the 40 ms congestion threshold. "
            "The policy uses the conservative congestion fallback."
        )
    elif config["signal_dbm"] <= -80:
        st.success(
            "Weak signal with queue delay below 40 ms: timeout losses are "
            "classified as likely wireless impairment."
        )
    else:
        st.info(
            "The measurements do not strongly indicate wireless impairment "
            "or congestion. The policy uses the conservative uncertain fallback."
        )

    if any(result["error"] for result in results.values()):
        st.subheader("Simulation errors")
        for label, result in results.items():
            if result["error"]:
                st.error(f"{label}: {result['error']}")

st.divider()
st.caption(
    "Educational simulator only — not a modified operating-system TCP stack. "
    "Link measurements are simulated inputs; results describe this model's assumptions."
)
