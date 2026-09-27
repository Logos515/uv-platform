from abc import ABC, abstractmethod
from uavvln.core.action import AgentAction
from uavvln.core.state import UAVState

class DynamicsBackend(ABC):
    @abstractmethod
    def reset(self, initial_state: UAVState) -> UAVState: ...
    @abstractmethod
    def step(self, control: AgentAction, dt: float) -> UAVState: ...
    @abstractmethod
    def get_state(self) -> UAVState: ...
    @abstractmethod
    def set_state(self, state: UAVState) -> None: ...
    def capabilities(self):
        return {"kinematics"}
