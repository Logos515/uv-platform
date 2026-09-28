"""Convert protocol actions to AirSim-compatible velocity commands."""
from dataclasses import dataclass
import numpy as np
from uavvln.core.action import DiscreteAction
from uavvln.core.transform import canonical_velocity_to_ned

@dataclass(frozen=True)
class VelocityCommand:
    velocity_ned: np.ndarray
    duration: float
    yaw_rate: float = 0.0

class DiscreteController:
    def __init__(self, speed=1.0, turn_rate=0.5, duration=0.5):
        self.speed = float(speed); self.turn_rate = float(turn_rate); self.duration = float(duration)
    def reset(self): pass
    def convert(self, agent_action, current_state):
        if not isinstance(agent_action, DiscreteAction): raise TypeError("DiscreteController expects DiscreteAction")
        magnitude = abs(float(agent_action.magnitude)); speed = self.speed * magnitude
        yaw = current_state.pose.yaw
        velocity = np.zeros(3); yaw_rate = 0.0
        if agent_action.name == "forward": velocity = np.array([np.cos(yaw), np.sin(yaw), 0.0]) * speed
        elif agent_action.name == "ascend": velocity[2] = speed
        elif agent_action.name == "descend": velocity[2] = -speed
        elif agent_action.name == "turn_left": yaw_rate = self.turn_rate * magnitude
        elif agent_action.name == "turn_right": yaw_rate = -self.turn_rate * magnitude
        return VelocityCommand(canonical_velocity_to_ned(velocity), self.duration, yaw_rate)
