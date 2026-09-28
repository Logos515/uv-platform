class UnrealGeometry:
    def __init__(self, client=None, vehicle_name=""):
        if client is None:
            try:
                import airsim
            except ImportError as exc:
                raise ImportError("UnrealGeometry requires airsim or an injected client") from exc
            client = airsim.MultirotorClient()
        self.client = client; self.vehicle_name = vehicle_name
    def collision(self, pose):
        info = self.client.simGetCollisionInfo(vehicle_name=self.vehicle_name)
        return bool(getattr(info, "has_collided", False))
    def distance_to_obstacle(self, pose):
        getter = getattr(self.client, "getDistanceSensorData", None)
        if getter is None: return float("inf")
        try:
            data = getter(vehicle_name=self.vehicle_name)
            return float(getattr(data, "distance", float("inf")))
        except Exception: return float("inf")
    def capabilities(self): return {"collision", "distance_query"}
