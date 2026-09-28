from dataclasses import dataclass, field
from .observation import CameraSpec

@dataclass(frozen=True)
class ObservationSpec:
    modalities: tuple[str, ...] = ("rgb",)
    cameras: tuple[CameraSpec, ...] = (CameraSpec(),)
    history_length: int = 1
    pose_visible: bool = False
    depth_dtype: str = "float32"
    def __post_init__(self):
        if self.history_length <= 0: raise ValueError("history_length must be positive")
