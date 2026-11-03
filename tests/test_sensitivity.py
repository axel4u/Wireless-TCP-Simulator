import pytest

from run_sensitivity import classify_grid_point


@pytest.mark.parametrize(
    ("signal", "queue", "expected"),
    [
        (-79, 39, "UNCERTAIN"),
        (-80, 39, "WIRELESS"),
        (-81, 39, "WIRELESS"),
        (-79, 40, "CONGESTION"),
        (-80, 40, "CONGESTION"),
        (-81, 40, "CONGESTION"),
        (-79, 41, "CONGESTION"),
        (-80, 41, "CONGESTION"),
        (-81, 41, "CONGESTION"),
    ],
)
def test_signal_and_queue_sensitivity_grid(signal, queue, expected):
    assert classify_grid_point(signal, queue, 40, -80) == expected
