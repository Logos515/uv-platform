from uavvln.core.observation import Observation
from .camera import CameraSensor
from .depth import DepthSensor
from .pose import PoseSensor

class SensorSuite:
    def __init__(self, camera, modalities=("rgb",), pose_visible=False):
        self.camera = camera; self.modalities = tuple(modalities); self.pose_visible = pose_visible
        self.rgb = CameraSensor(camera); self.depth = DepthSensor(camera); self.pose = PoseSensor()
    def reset(self): pass
    def observe(self, renderer, state, instruction, timestamp, info):
        rgb = {self.camera.name: self.rgb.read(renderer, state.pose)} if "rgb" in self.modalities else {}
        depth = {self.camera.name: self.depth.read(renderer, state.pose)} if "depth" in self.modalities else {}
        return Observation(rgb=rgb, depth=depth, pose=state.pose if self.pose_visible else None,
                           instruction=instruction, timestamp=timestamp, info=info)
