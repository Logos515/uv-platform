from dataclasses import dataclass, field
from typing import Any
import numpy as np
from .pose import Pose

@dataclass(frozen=True)
class CameraSpec:
    name: str = "front"
    width: int = 64
    height: int = 64
    fov_degrees: float = 90.0
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    quaternion: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)

    def __post_init__(self):
        if self.width <= 0 or self.height <= 0:
            raise ValueError("camera dimensions must be positive")

@dataclass(frozen=True)
class RenderOutput:
    rgb: np.ndarray | None = None
    depth: np.ndarray | None = None
    semantic: np.ndarray | None = None

@dataclass(frozen=True)
class Observation:
    rgb: dict[str, np.ndarray] = field(default_factory=dict)
    depth: dict[str, np.ndarray] = field(default_factory=dict)
    pose: Pose | None = None
    imu: Any = None
    gps: Any = None
    semantic_map: Any = None
    geographic_map: Any = None
    instruction: str | None = None
    assistant_message: str | None = None
    timestamp: float = 0.0
    info: dict = field(default_factory=dict)

    def copy(self):
        return Observation(
            rgb={k: v.copy() for k, v in self.rgb.items()},
            depth={k: v.copy() for k, v in self.depth.items()}, pose=self.pose,
            imu=self.imu, gps=self.gps, semantic_map=self.semantic_map,
            geographic_map=self.geographic_map, instruction=self.instruction,
            assistant_message=self.assistant_message, timestamp=self.timestamp,
            info=dict(self.info),
        )
