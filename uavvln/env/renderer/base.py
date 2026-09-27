from abc import ABC, abstractmethod
from uavvln.core.observation import CameraSpec, RenderOutput
from uavvln.core.pose import Pose

class RendererBackend(ABC):
    def load_scene(self, scene_id: str): return None
    @abstractmethod
    def render(self, camera: CameraSpec, pose: Pose, modalities: list[str]) -> RenderOutput: ...
    def capabilities(self): return {"rgb"}
