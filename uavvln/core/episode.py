from dataclasses import dataclass, field
from typing import Any
import numpy as np
from .pose import Pose

class GoalSpec: pass

@dataclass(frozen=True)
class PointGoal(GoalSpec):
    position: np.ndarray
    success_radius: float = 1.0
    def __post_init__(self):
        p = np.asarray(self.position, dtype=np.float64)
        if p.shape != (3,): raise ValueError("goal position must have shape (3,)")
        if self.success_radius <= 0: raise ValueError("success_radius must be positive")
        object.__setattr__(self, "position", p.copy())

@dataclass(frozen=True)
class EpisodeSpec:
    episode_id: str
    scene_id: str
    instruction: str
    start_pose: Pose
    goal: GoalSpec
    demonstration: Any = None
    metadata: dict = field(default_factory=dict)
