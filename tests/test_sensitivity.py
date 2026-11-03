import pytest

from run_sensitivity import classify_grid_point


@pytest.mark.parametrize(
    ("signal", "queue", "expected"),
    [
        (-79, 39, "uncertain"),
        (-80, 39, "likely_wireless"),
        (-81, 39, "likely_wireless"),
        (-79, 40, "likely_congestion"),
        (-80, 40, "likely_congestion"),
        (-81, 40, "likely_congestion"),
        (-79, 41, "likely_congestion"),
        (-80, 41, "likely_congestion"),
        (-81, 41, "likely_congestion"),
    ],
)
def test_signal_and_queue_sensitivity_grid(signal, queue, expected):
    assert classify_grid_point(signal, queue, 40, -80) == expected
