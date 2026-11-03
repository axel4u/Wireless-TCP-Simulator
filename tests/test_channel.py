from simulator.channel import WirelessChannel
from simulator.event_scheduler import EventScheduler
from simulator.packet import Packet, PacketType


def test_zero_loss_delivers_after_configured_delay():
    scheduler = EventScheduler()
    channel = WirelessChannel(scheduler, loss_probability=0, delay_ms=12, seed=1)
    packet = Packet(PacketType.DATA, 0, 1000, 0)
    received = []
    channel.transmit(packet, received.append)
    assert received == []
    scheduler.run()
    assert received == [packet]
    assert scheduler.now_ms == 12


def test_total_loss_drops_packet():
    scheduler = EventScheduler()
    channel = WirelessChannel(scheduler, loss_probability=1, delay_ms=12, seed=1)
    packet = Packet(PacketType.DATA, 0, 1000, 0)
    received = []
    channel.transmit(packet, received.append)
    scheduler.run()
    assert received == []
    assert channel.dropped_count == 1


def test_burst_loss_model_is_seed_deterministic():
    from simulator.burst_loss import GilbertElliottLoss

    first = GilbertElliottLoss(seed=19)
    second = GilbertElliottLoss(seed=19)
    outcomes_first = [first.should_drop() for _ in range(100)]
    outcomes_second = [second.should_drop() for _ in range(100)]
    assert outcomes_first == outcomes_second
    assert first.state_history == second.state_history


def test_burst_loss_model_can_enter_bad_state():
    from simulator.burst_loss import GilbertElliottLoss

    model = GilbertElliottLoss(
        good_to_bad_probability=1.0,
        bad_to_good_probability=0.0,
        good_state_loss_probability=0.0,
        bad_state_loss_probability=1.0,
        seed=1,
    )
    assert model.should_drop() is True
    assert model.state == model.BAD


def test_burst_loss_model_validates_probabilities():
    import pytest
    from simulator.burst_loss import GilbertElliottLoss

    with pytest.raises(ValueError):
        GilbertElliottLoss(bad_state_loss_probability=1.1)


def test_channel_rejects_two_loss_models():
    import pytest
    from simulator.burst_loss import GilbertElliottLoss
    from simulator.loss_trace import SharedLossTrace

    scheduler = EventScheduler()
    with pytest.raises(ValueError):
        WirelessChannel(
            scheduler,
            loss_probability=0.1,
            loss_trace=SharedLossTrace(0.1),
            burst_loss_model=GilbertElliottLoss(),
        )


def test_channel_uses_burst_loss_model():
    from simulator.burst_loss import GilbertElliottLoss

    scheduler = EventScheduler()
    model = GilbertElliottLoss(
        good_to_bad_probability=1.0,
        bad_to_good_probability=0.0,
        good_state_loss_probability=0.0,
        bad_state_loss_probability=1.0,
    )
    channel = WirelessChannel(scheduler, burst_loss_model=model)
    packet = Packet(PacketType.DATA, 0, 1000, 0)
    received = []
    channel.transmit(packet, received.append)
    scheduler.run()
    assert received == []
    assert channel.dropped_count == 1
