from dataclasses import dataclass, field
from typing import Literal
import numpy as np

class AgentAction:  # marker base class for protocol actions
    pass

@dataclass(frozen=True)
class DiscreteAction(AgentAction):
    name: Literal["forward", "turn_left", "turn_right", "ascend", "descend", "stop"]
    magnitude: float = 1.0
    def __post_init__(self):
        allowed = {"forward", "turn_left", "turn_right", "ascend", "descend", "stop"}
        if self.name not in allowed:
            raise ValueError(f"unknown discrete action: {self.name}")

@dataclass(frozen=True)
class VelocityAction(AgentAction):
    velocity: np.ndarray
    yaw_rate: float = 0.0
    def __post_init__(self):
        v = np.asarray(self.velocity, dtype=np.float64)
        if v.shape != (3,):
            raise ValueError("velocity must have shape (3,)")
        object.__setattr__(self, "velocity", v.copy())

@dataclass(frozen=True)
class WaypointAction(AgentAction):
    position: np.ndarray
    yaw: float = 0.0
    def __post_init__(self):
        p = np.asarray(self.position, dtype=np.float64)
        if p.shape != (3,):
            raise ValueError("waypoint position must have shape (3,)")
        object.__setattr__(self, "position", p.copy())

@dataclass(frozen=True)
class ActionChunk(AgentAction):
    actions: np.ndarray
    def __post_init__(self):
        a = np.asarray(self.actions, dtype=np.float64)
        if a.ndim != 2:
            raise ValueError("actions must be a [T, D] array")
        object.__setattr__(self, "actions", a.copy())
