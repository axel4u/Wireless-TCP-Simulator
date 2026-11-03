"""Two-state Gilbert-Elliott burst-loss model for wireless channels."""
from __future__ import annotations

import random


class GilbertElliottLoss:
    """Model correlated packet loss using GOOD and BAD channel states.

    The channel starts in GOOD. At each transmission attempt it first applies
    the state transition probabilities, then samples loss probability for the
    resulting state. BAD periods can therefore create consecutive losses.
    """

    GOOD = "GOOD"
    BAD = "BAD"

    def __init__(
        self,
        good_to_bad_probability: float = 0.02,
        bad_to_good_probability: float = 0.25,
        good_state_loss_probability: float = 0.01,
        bad_state_loss_probability: float = 0.80,
        seed: int = 7,
    ) -> None:
        probabilities = {
            "good_to_bad_probability": good_to_bad_probability,
            "bad_to_good_probability": bad_to_good_probability,
            "good_state_loss_probability": good_state_loss_probability,
            "bad_state_loss_probability": bad_state_loss_probability,
        }
        for name, value in probabilities.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        self.good_to_bad_probability = good_to_bad_probability
        self.bad_to_good_probability = bad_to_good_probability
        self.good_state_loss_probability = good_state_loss_probability
        self.bad_state_loss_probability = bad_state_loss_probability
        self.state = self.GOOD
        self._rng = random.Random(seed)
        self.state_history: list[str] = []

    def should_drop(self) -> bool:
        """Advance the channel state and return this attempt's loss outcome."""
        transition_draw = self._rng.random()
        if self.state == self.GOOD:
            if transition_draw < self.good_to_bad_probability:
                self.state = self.BAD
        elif transition_draw < self.bad_to_good_probability:
            self.state = self.GOOD

        self.state_history.append(self.state)
        loss_probability = (
            self.good_state_loss_probability
            if self.state == self.GOOD
            else self.bad_state_loss_probability
        )
        return self._rng.random() < loss_probability
