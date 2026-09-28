from uavvln.core.observation import CameraSpec

class DepthSensor:
    modality = "depth"
    def __init__(self, camera: CameraSpec): self.camera = camera
    def read(self, renderer, pose):
        return renderer.render(self.camera, pose, ["depth"]).depth
