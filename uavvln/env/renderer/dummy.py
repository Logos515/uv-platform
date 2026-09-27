import numpy as np
from .base import RendererBackend
from uavvln.core.observation import CameraSpec, RenderOutput

class DummyRenderer(RendererBackend):
    """Returns deterministic, shape-correct images without a simulator."""
    def __init__(self, seed=0): self.seed = seed
    def render(self, camera: CameraSpec, pose, modalities):
        value = np.uint8((self.seed + int(round(pose.timestamp if hasattr(pose, 'timestamp') else 0))) % 255)
        rgb = np.full((camera.height, camera.width, 3), value, dtype=np.uint8) if "rgb" in modalities else None
        depth = np.full((camera.height, camera.width), 100.0, dtype=np.float32) if "depth" in modalities else None
        return RenderOutput(rgb=rgb, depth=depth)
