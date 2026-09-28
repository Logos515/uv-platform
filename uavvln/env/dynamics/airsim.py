"""Optional AirSim dynamics adapter.

The module intentionally does not import the AirSim package at module import
time. A real client or a test double can be supplied to the constructor.
"""
import numpy as np
from dataclasses import replace
from .base import DynamicsBackend
from uavvln.core.action import DiscreteAction, VelocityAction, WaypointAction
from uavvln.core.pose import Pose
from uavvln.core.state import UAVState
from uavvln.core.transform import (canonical_position_to_ned,
    canonical_quaternion_to_ned, ned_position_to_canonical,
    ned_quaternion_to_canonical, canonical_velocity_to_ned)

class AirSimDynamicsBackend(DynamicsBackend):
    def __init__(self, client=None, vehicle_name="", max_speed=5.0):
        if client is None:
            try:
                import airsim
            except ImportError as exc:
                raise ImportError("AirSimDynamicsBackend requires airsim or an injected client") from exc
            client = airsim.MultirotorClient()
        self.client = client; self.vehicle_name = vehicle_name; self.max_speed = float(max_speed)
        self._state = UAVState(Pose.identity())

    def reset(self, initial_state):
        self.client.reset()
        self.set_state(initial_state)
        self._state = self.get_state()
        return self._state

    def set_state(self, state):
        pose = self._make_airsim_pose(state.pose)
        setter = getattr(self.client, "simSetVehiclePose", None)
        if setter is not None:
            setter(pose, True, vehicle_name=self.vehicle_name)
        self._state = state

    def get_state(self):
        native = self.client.getMultirotorState(vehicle_name=self.vehicle_name)
        kin = native.kinematics_estimated
        pos = ned_position_to_canonical(self._xyz(kin.position_val))
        quat = ned_quaternion_to_canonical(self._quat(kin.orientation))
        vel = ned_position_to_canonical(self._xyz(kin.linear_velocity))
        ang = ned_position_to_canonical(self._xyz(kin.angular_velocity))
        timestamp = float(getattr(native, "timestamp", 0.0)) / 1e9
        self._state = UAVState(Pose(pos, quat), vel, ang, max(0.0, timestamp))
        return self._state

    def step(self, control, dt):
        if dt <= 0: raise ValueError("dt must be positive")
        velocity, yaw_rate = self._command_velocity(control)
        velocity_ned = canonical_velocity_to_ned(velocity)
        try:
            future = self.client.moveByVelocityAsync(float(velocity_ned[0]), float(velocity_ned[1]),
                float(velocity_ned[2]), float(dt), vehicle_name=self.vehicle_name)
        except TypeError:
            future = self.client.moveByVelocityAsync(float(velocity_ned[0]), float(velocity_ned[1]),
                float(velocity_ned[2]), float(dt))
        if hasattr(future, "join"): future.join()
        return self.get_state()

    def _command_velocity(self, action):
        state = self.get_state()
        if isinstance(action, VelocityAction):
            return np.clip(action.velocity, -self.max_speed, self.max_speed), action.yaw_rate
        if isinstance(action, WaypointAction):
            delta = action.position - state.pose.position; distance = np.linalg.norm(delta)
            velocity = delta / distance * min(self.max_speed, distance) if distance > 1e-9 else np.zeros(3)
            return velocity, 0.0
        if isinstance(action, DiscreteAction):
            magnitude = min(self.max_speed, abs(float(action.magnitude)))
            yaw = state.pose.yaw
            if action.name == "forward": return np.array([np.cos(yaw), np.sin(yaw), 0.0]) * magnitude, 0.0
            if action.name == "ascend": return np.array([0.0, 0.0, magnitude]), 0.0
            if action.name == "descend": return np.array([0.0, 0.0, -magnitude]), 0.0
            return np.zeros(3), magnitude if action.name == "turn_left" else -magnitude
        raise TypeError(f"unsupported AirSim action: {type(action).__name__}")

    def _make_airsim_pose(self, pose):
        try:
            import airsim
            p = canonical_position_to_ned(pose.position); q = canonical_quaternion_to_ned(pose.quaternion)
            return airsim.Pose(airsim.Vector3r(*p), airsim.Quaternionr(*q))
        except ImportError:
            return {"position": canonical_position_to_ned(pose.position),
                    "quaternion": canonical_quaternion_to_ned(pose.quaternion)}

    @staticmethod
    def _xyz(value): return np.array([value.x_val, value.y_val, value.z_val], dtype=np.float64)
    @staticmethod
    def _quat(value): return np.array([value.x_val, value.y_val, value.z_val, value.w_val], dtype=np.float64)
    def capabilities(self): return {"airsim", "kinematics", "discrete", "velocity"}
