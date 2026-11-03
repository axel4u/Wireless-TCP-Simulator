from simulator.channel import WirelessChannel
from simulator.event_scheduler import EventScheduler
from simulator.loss_trace import SharedLossTrace
from simulator.packet import Packet, PacketType


def test_shared_trace_repeats_same_outcome_for_same_transmission_key():
    trace = SharedLossTrace(loss_probability=0.35, seed=19)
    first = [
        trace.should_drop(PacketType.DATA, sequence_number=4, attempt_number=n)
        for n in range(1, 8)
    ]
    second = [
        trace.should_drop(PacketType.DATA, sequence_number=4, attempt_number=n)
        for n in range(1, 8)
    ]
    assert first == second


def test_shared_trace_is_independent_of_transmission_order():
    trace = SharedLossTrace(loss_probability=0.4, seed=23)
    expected = trace.should_drop(PacketType.DATA, 2, 1)
    trace.should_drop(PacketType.ACK, 99, 3)
    assert trace.should_drop(PacketType.DATA, 2, 1) == expected


def test_two_channels_share_outcomes_for_corresponding_attempts():
    trace = SharedLossTrace(loss_probability=0.3, seed=7)
    channels = [
        WirelessChannel(EventScheduler(), 0.3, seed=7, loss_trace=trace),
        WirelessChannel(EventScheduler(), 0.3, seed=7, loss_trace=trace),
    ]
    outcomes = []
    for channel in channels:
        received = []
        for attempt in range(3):
            packet = Packet(PacketType.DATA, 5, 1000, 0, retransmission=attempt > 0)
            channel.transmit(packet, received.append)
        outcomes.append(channel.dropped_count)
    assert outcomes[0] == outcomes[1]


def test_shared_trace_validates_probability():
    trace = SharedLossTrace(loss_probability=0.2, seed=1)
    try:
        WirelessChannel(EventScheduler(), 0.3, loss_trace=trace)
    except ValueError as error:
        assert "must match" in str(error)
    else:
        raise AssertionError("mismatched trace probability should be rejected")


def test_random_mode_remains_seed_deterministic():
    outcomes = []
    for _ in range(2):
        scheduler = EventScheduler()
        channel = WirelessChannel(scheduler, loss_probability=0.3, seed=11)
        packet = Packet(PacketType.DATA, 0, 1000, 0)
        channel.transmit(packet, lambda _: None)
        outcomes.append(channel.dropped_count)
    assert outcomes[0] == outcomes[1]
