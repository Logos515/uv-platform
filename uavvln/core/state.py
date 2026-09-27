from dataclasses import dataclass, field
import numpy as np
from .pose import Pose

def _vec(value, name):
    a = np.asarray(value, dtype=np.float64)
    if a.shape != (3,):
        raise ValueError(f"{name} must have shape (3,), got {a.shape}")
    return a.copy()

@dataclass(frozen=True)
class UAVState:
    pose: Pose
    linear_velocity: np.ndarray = field(default_factory=lambda: np.zeros(3))
    angular_velocity: np.ndarray = field(default_factory=lambda: np.zeros(3))
    timestamp: float = 0.0

    def __post_init__(self):
        object.__setattr__(self, "linear_velocity", _vec(self.linear_velocity, "linear_velocity"))
        object.__setattr__(self, "angular_velocity", _vec(self.angular_velocity, "angular_velocity"))
        if self.timestamp < 0:
            raise ValueError("timestamp must be non-negative")

@dataclass(frozen=True)
class PrivilegedState:
    state: UAVState
    goal_position: np.ndarray | None = None
    collision: bool = False
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.goal_position is not None:
            object.__setattr__(self, "goal_position", _vec(self.goal_position, "goal_position"))
