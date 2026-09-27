from abc import ABC, abstractmethod
class GeometryBackend(ABC):
    @abstractmethod
    def collision(self, pose): ...
    def raycast(self, origin, direction): return None
    def distance_to_obstacle(self, pose): return float("inf")
