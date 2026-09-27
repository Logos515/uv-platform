import numpy as np

from uavvln.agents import RandomAgent
from uavvln.benchmarks import ToyBenchmark
from uavvln.core.action import VelocityAction
from uavvln.core.pose import Pose
from uavvln.core.state import UAVState
from uavvln.env.dynamics import KinematicBackend
from uavvln.env.environment import UAVEnvironment
from uavvln.env.geometry import NoGeometry
from uavvln.env.renderer import DummyRenderer
from uavvln.runtime import Runner

def make_environment():
    return UAVEnvironment(KinematicBackend(), DummyRenderer(), NoGeometry())

def test_kinematic_backend_integrates_velocity():
    backend = KinematicBackend()
    backend.reset(UAVState(Pose.identity()))
    state = backend.step(VelocityAction(np.array([1.0, 0.0, 0.0])), 0.5)
    assert np.allclose(state.pose.position, [0.5, 0.0, 0.0])
    assert state.timestamp == 0.5

def test_phase0_episode_runs_to_success():
    result = Runner(ToyBenchmark(), make_environment(), RandomAgent()).evaluate()[0]
    assert result.success
    assert result.steps > 0
    assert result.collisions == 0

def test_privileged_state_is_not_public_observation():
    environment = make_environment()
    episode = ToyBenchmark().episodes()[0]
    observation = environment.reset(episode)
    assert observation.pose is None
    step = environment.step(__import__('uavvln').DiscreteAction("forward", 0.5))
    assert step.privileged_state.goal_position is not None
