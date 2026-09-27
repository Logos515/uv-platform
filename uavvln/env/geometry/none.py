from .base import GeometryBackend
class NoGeometry(GeometryBackend):
    def collision(self, pose): return False
