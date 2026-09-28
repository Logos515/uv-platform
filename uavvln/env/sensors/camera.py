from uavvln.core.observation import CameraSpec

class CameraSensor:
    modality = "rgb"
    def __init__(self, camera: CameraSpec): self.camera = camera
    def read(self, renderer, pose):
        return renderer.render(self.camera, pose, ["rgb"]).rgb
