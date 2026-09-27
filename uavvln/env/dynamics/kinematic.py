"""Deterministic, simulator-free point-mass dynamics for protocol tests."""
from dataclasses import replace
import numpy as np
from .base import DynamicsBackend
from uavvln.core.action import AgentAction, DiscreteAction, VelocityAction, WaypointAction
from uavvln.core.pose import Pose
from uavvln.core.state import UAVState

class KinematicBackend(DynamicsBackend):
    def __init__(self, max_speed=5.0, max_yaw_rate=3.14):
        self.max_speed = float(max_speed)
        self.max_yaw_rate = float(max_yaw_rate)
        self._state = UAVState(pose=Pose.identity())

    def reset(self, initial_state):
        self.set_state(initial_state)
        return self._state

    def set_state(self, state):
        if not isinstance(state, UAVState): raise TypeError("state must be UAVState")
        self._state = state

    def get_state(self): return self._state

    def step(self, control: AgentAction, dt: float):
        if dt <= 0: raise ValueError("dt must be positive")
        velocity = np.zeros(3)
        yaw_rate = 0.0
        if isinstance(control, VelocityAction):
            velocity = np.clip(control.velocity, -self.max_speed, self.max_speed)
            yaw_rate = float(np.clip(control.yaw_rate, -self.max_yaw_rate, self.max_yaw_rate))
        elif isinstance(control, WaypointAction):
            delta = control.position - self._state.pose.position
            distance = np.linalg.norm(delta)
            if distance > 1e-9: velocity = delta / distance * min(self.max_speed, distance / dt)
            yaw_rate = float(np.clip((control.yaw - self._state.pose.yaw) / dt, -self.max_yaw_rate, self.max_yaw_rate))
        elif isinstance(control, DiscreteAction):
            magnitude = abs(float(control.magnitude))
            if control.name == "forward": velocity[0] = min(self.max_speed, magnitude)
            elif control.name == "ascend": velocity[2] = min(self.max_speed, magnitude)
            elif control.name == "descend": velocity[2] = -min(self.max_speed, magnitude)
            elif control.name == "turn_left": yaw_rate = min(self.max_yaw_rate, magnitude)
            elif control.name == "turn_right": yaw_rate = -min(self.max_yaw_rate, magnitude)
        else:
            raise TypeError(f"unsupported action: {type(control).__name__}")
        position = self._state.pose.position + velocity * dt
        pose = self._state.pose.with_position(position).with_yaw(self._state.pose.yaw + yaw_rate * dt)
        self._state = replace(self._state, pose=pose, linear_velocity=velocity,
                              angular_velocity=np.array([0.0, 0.0, yaw_rate]),
                              timestamp=self._state.timestamp + dt)
        return self._state
