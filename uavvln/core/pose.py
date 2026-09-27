"""Canonical geometry types: right-handed, Z-up, metres, radians, xyzw quaternions."""
from dataclasses import dataclass
import numpy as np

CANONICAL_FRAME = "world"

def _vector(value, size, name):
    result = np.asarray(value, dtype=np.float64)
    if result.shape != (size,):
        raise ValueError(f"{name} must have shape ({size},), got {result.shape}")
    return result.copy()

@dataclass(frozen=True)
class Pose:
    position: np.ndarray
    quaternion: np.ndarray = (0.0, 0.0, 0.0, 1.0)
    frame: str = CANONICAL_FRAME

    def __post_init__(self):
        object.__setattr__(self, "position", _vector(self.position, 3, "position"))
        q = _vector(self.quaternion, 4, "quaternion")
        norm = np.linalg.norm(q)
        if norm < 1e-12:
            raise ValueError("quaternion must be non-zero")
        object.__setattr__(self, "quaternion", q / norm)
        if not self.frame:
            raise ValueError("frame must be non-empty")

    @classmethod
    def identity(cls, frame=CANONICAL_FRAME):
        return cls(np.zeros(3), (0, 0, 0, 1), frame)

    @property
    def xyz(self):
        return self.position

    @property
    def yaw(self):
        x, y, z, w = self.quaternion
        return float(np.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)))

    def with_position(self, position):
        return Pose(position, self.quaternion, self.frame)

    def with_yaw(self, yaw):
        return Pose(self.position, (0.0, 0.0, np.sin(yaw / 2), np.cos(yaw / 2)), self.frame)
