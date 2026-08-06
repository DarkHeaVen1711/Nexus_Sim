"""Signal controller state machine for one intersection (TR-ML-03).

Mirrors the C++ ``SignalController`` (engine/src/agent/SignalController.h)
state machine — GREEN / YELLOW / RED with a phase timer — so the trained policy
transfers conceptually to the engine in Phase 8/12. The agent decision happens
only at a GREEN-phase boundary, matching the ``{EXTEND, SWITCH}`` action space.
"""

from __future__ import annotations

ACTION_EXTEND = 0
ACTION_SWITCH = 1


class IntersectionController:
    """Green/yellow/red state machine with phase-boundary decisions."""

    def __init__(
        self,
        decision_interval: float = 5.0,
        yellow_time: float = 3.0,
        red_clearance: float = 2.0,
    ):
        self.phase = 0
        self.state = "GREEN"
        self.timer = decision_interval
        self.time_in_phase = 0.0
        self.decision_interval = decision_interval
        self.yellow_time = yellow_time
        self.red_clearance = red_clearance

    def is_decision_ready(self) -> bool:
        """True when the GREEN phase timer has elapsed and an action is needed."""
        return self.state == "GREEN" and self.timer <= 0.0

    def apply_action(self, action: int) -> None:
        """Apply EXTEND/SWITCH at a phase boundary; ignored otherwise."""
        if not self.is_decision_ready():
            return
        self.time_in_phase = 0.0
        if action == ACTION_EXTEND:
            self.timer = self.decision_interval
        else:
            self.state = "YELLOW"
            self.timer = self.yellow_time

    def step(self, dt: float) -> None:
        """Advance the state machine by ``dt`` seconds."""
        if self.state == "GREEN":
            if self.timer > 0.0:
                self.timer -= dt
                self.time_in_phase += dt
                if self.timer <= 0.0:
                    self.timer = 0.0
        elif self.state == "YELLOW":
            self.timer -= dt
            if self.timer <= 0.0:
                self.state = "RED"
                self.timer = self.red_clearance
        elif self.state == "RED":
            self.timer -= dt
            if self.timer <= 0.0:
                self.phase = 1 - self.phase
                self.state = "GREEN"
                self.timer = self.decision_interval
                self.time_in_phase = 0.0

    def is_green(self, approach_idx: int, green_approaches) -> bool:
        """True when ``approach_idx`` is in the currently green phase."""
        if self.state != "GREEN":
            return False
        return approach_idx in green_approaches[self.phase]
