from dataclasses import dataclass
import numpy as np
from uavvln.core.action import AgentAction
from uavvln.core.episode import EpisodeSpec
from uavvln.core.observation import CameraSpec, Observation
from uavvln.core.state import PrivilegedState, UAVState
from .dynamics.base import DynamicsBackend
from .geometry.base import GeometryBackend
from .renderer.base import RendererBackend

@dataclass(frozen=True)
class StepResult:
    observation: Observation
    reward: float
    terminated: bool
    truncated: bool
    info: dict
    privileged_state: PrivilegedState

    def __iter__(self):
        """Allow the familiar ``obs, reward, terminated, truncated, info`` form."""
        yield self.observation
        yield self.reward
        yield self.terminated
        yield self.truncated
        yield self.info

class UAVEnvironment:
    def __init__(self, dynamics: DynamicsBackend, renderer: RendererBackend,
                 geometry: GeometryBackend, dt=0.1, camera: CameraSpec | None = None):
        self.dynamics, self.renderer, self.geometry = dynamics, renderer, geometry
        self.dt = float(dt); self.camera = camera or CameraSpec()
        self.episode = None; self.steps = 0

    def reset(self, episode: EpisodeSpec):
        self.episode = episode; self.steps = 0
        self.dynamics.reset(UAVState(episode.start_pose))
        self.renderer.load_scene(episode.scene_id)
        return self.observe()

    def observe(self):
        if self.episode is None: raise RuntimeError("reset must be called before observe")
        state = self.dynamics.get_state()
        rendered = self.renderer.render(self.camera, state.pose, ["rgb"])
        obs = Observation(rgb={self.camera.name: rendered.rgb}, pose=None,
                          instruction=self.episode.instruction, timestamp=state.timestamp,
                          info={"step": self.steps, "scene_id": self.episode.scene_id})
        return obs

    def step(self, action: AgentAction):
        if self.episode is None: raise RuntimeError("reset must be called before step")
        state = self.dynamics.step(action, self.dt); self.steps += 1
        goal = self.episode.goal
        distance = float(np.linalg.norm(state.pose.position - goal.position))
        success = distance <= goal.success_radius
        collision = bool(self.geometry.collision(state.pose))
        terminated = success or collision
        truncated = self.steps >= self._max_steps()
        reward = (1.0 if success else 0.0) - (1.0 if collision else 0.0)
        info = {"distance_to_goal": distance, "success": success, "collision": collision, "step": self.steps}
        privileged = PrivilegedState(state, goal.position, collision, info)
        return StepResult(self.observe(), reward, terminated, truncated, info, privileged)

    def _max_steps(self):
        return int(self.episode.metadata.get("max_steps", 100))
