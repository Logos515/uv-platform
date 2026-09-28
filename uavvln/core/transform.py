"""Rigid transforms in the canonical right-handed Z-up frame."""
from dataclasses import dataclass
import numpy as np
from .pose import Pose

def _q(value):
    q = np.asarray(value, dtype=np.float64)
    if q.shape != (4,): raise ValueError("quaternion must have shape (4,)")
    n = np.linalg.norm(q)
    if n < 1e-12: raise ValueError("quaternion must be non-zero")
    return q / n

def quaternion_to_matrix(quaternion_xyzw):
    x, y, z, w = _q(quaternion_xyzw)
    return np.array([
        [1 - 2*(y*y + z*z), 2*(x*y - z*w), 2*(x*z + y*w)],
        [2*(x*y + z*w), 1 - 2*(x*x + z*z), 2*(y*z - x*w)],
        [2*(x*z - y*w), 2*(y*z + x*w), 1 - 2*(x*x + y*y)],
    ])

def matrix_to_quaternion(matrix):
    m = np.asarray(matrix, dtype=np.float64)
    if m.shape != (3, 3): raise ValueError("rotation matrix must be 3x3")
    trace = np.trace(m)
    if trace > 0:
        s = 2 * np.sqrt(trace + 1.0); w = .25 * s
        x = (m[2,1] - m[1,2]) / s; y = (m[0,2] - m[2,0]) / s; z = (m[1,0] - m[0,1]) / s
    elif m[0,0] > m[1,1] and m[0,0] > m[2,2]:
        s = 2 * np.sqrt(1 + m[0,0] - m[1,1] - m[2,2]); w = (m[2,1]-m[1,2])/s
        x = .25*s; y = (m[0,1]+m[1,0])/s; z = (m[0,2]+m[2,0])/s
    elif m[1,1] > m[2,2]:
        s = 2 * np.sqrt(1 + m[1,1] - m[0,0] - m[2,2]); w = (m[0,2]-m[2,0])/s
        x = (m[0,1]+m[1,0])/s; y = .25*s; z = (m[1,2]+m[2,1])/s
    else:
        s = 2 * np.sqrt(1 + m[2,2] - m[0,0] - m[1,1]); w = (m[1,0]-m[0,1])/s
        x = (m[0,2]+m[2,0])/s; y = (m[1,2]+m[2,1])/s; z = .25*s
    return _q((x, y, z, w))

def ned_position_to_canonical(value):
    p = np.asarray(value, dtype=np.float64)
    if p.shape != (3,): raise ValueError("position must have shape (3,)")
    return np.array([p[0], p[1], -p[2]])

def canonical_position_to_ned(value):
    p = np.asarray(value, dtype=np.float64)
    if p.shape != (3,): raise ValueError("position must have shape (3,)")
    return np.array([p[0], p[1], -p[2]])

canonical_velocity_to_ned = canonical_position_to_ned
ned_velocity_to_canonical = ned_position_to_canonical

def ned_quaternion_to_canonical(value):
    # Reflect the NED Z axis on both sides of the rotation matrix.
    reflection = np.diag([1.0, 1.0, -1.0])
    return matrix_to_quaternion(reflection @ quaternion_to_matrix(value) @ reflection)

def canonical_quaternion_to_ned(value):
    reflection = np.diag([1.0, 1.0, -1.0])
    return matrix_to_quaternion(reflection @ quaternion_to_matrix(value) @ reflection)

@dataclass(frozen=True)
class Transform:
    translation: np.ndarray
    quaternion_xyzw: np.ndarray
    parent_frame: str
    child_frame: str
    def __post_init__(self):
        t = np.asarray(self.translation, dtype=np.float64)
        if t.shape != (3,): raise ValueError("translation must have shape (3,)")
        object.__setattr__(self, "translation", t.copy())
        object.__setattr__(self, "quaternion_xyzw", _q(self.quaternion_xyzw))
        if not self.parent_frame or not self.child_frame: raise ValueError("frame names are required")

    def apply(self, pose: Pose) -> Pose:
        position = self.translation + quaternion_to_matrix(self.quaternion_xyzw) @ pose.position
        quat = matrix_to_quaternion(quaternion_to_matrix(self.quaternion_xyzw) @ quaternion_to_matrix(pose.quaternion))
        return Pose(position, quat, self.parent_frame)
