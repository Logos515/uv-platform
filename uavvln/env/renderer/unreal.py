"""AirSim-backed Unreal renderer with RGB and depth conversion."""
import numpy as np
from .base import RendererBackend
from uavvln.core.observation import CameraSpec, RenderOutput

class UnrealRenderer(RendererBackend):
    def __init__(self, client=None, vehicle_name=""):
        if client is None:
            try:
                import airsim
            except ImportError as exc:
                raise ImportError("UnrealRenderer requires airsim or an injected client") from exc
            client = airsim.MultirotorClient()
        self.client = client; self.vehicle_name = vehicle_name; self.scene_id = None

    def load_scene(self, scene_id): self.scene_id = scene_id

    def render(self, camera: CameraSpec, pose, modalities):
        requests = [self._request(camera.name, "rgb" if "rgb" in modalities else "depth")]
        if "rgb" in modalities and "depth" in modalities:
            requests.append(self._request(camera.name, "depth"))
        responses = self.client.simGetImages(requests, vehicle_name=self.vehicle_name)
        rgb = depth = None
        for response in responses:
            kind = getattr(response, "kind", None) or getattr(response, "image_type", None)
            if kind in ("rgb", 0, "scene") and "rgb" in modalities:
                rgb = self._decode_rgb(response, camera)
            elif kind in ("depth", 1, "depth_planner") and "depth" in modalities:
                depth = self._decode_depth(response, camera)
        # Test doubles may return responses in request order without image_type.
        if rgb is None and "rgb" in modalities and responses: rgb = self._decode_rgb(responses[0], camera)
        if depth is None and "depth" in modalities:
            candidate = responses[-1]
            depth = self._decode_depth(candidate, camera)
        return RenderOutput(rgb=rgb, depth=depth)

    def _request(self, camera, modality):
        try:
            import airsim
            image_type = airsim.ImageType.Scene if modality == "rgb" else airsim.ImageType.DepthPlanar
            return airsim.ImageRequest(camera, image_type, modality == "depth", False)
        except ImportError:
            return {"camera_name": camera, "modality": modality}

    @staticmethod
    def _decode_rgb(response, camera):
        data = getattr(response, "image_data_uint8", b"")
        if isinstance(data, str): data = data.encode()
        raw = np.frombuffer(data, dtype=np.uint8)
        expected = camera.width * camera.height * 3
        if raw.size >= expected: return raw[:expected].reshape(camera.height, camera.width, 3)
        return np.zeros((camera.height, camera.width, 3), dtype=np.uint8)

    @staticmethod
    def _decode_depth(response, camera):
        data = getattr(response, "image_data_float", None)
        if data is None:
            raw = np.frombuffer(getattr(response, "image_data_uint8", b""), dtype=np.float32)
        else: raw = np.asarray(data, dtype=np.float32)
        expected = camera.width * camera.height
        if raw.size >= expected: return raw[:expected].reshape(camera.height, camera.width)
        return np.full((camera.height, camera.width), np.inf, dtype=np.float32)

    def capabilities(self): return {"rgb", "depth"}
