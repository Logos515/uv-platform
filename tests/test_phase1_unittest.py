import unittest
import numpy as np
from types import SimpleNamespace as NS

from uavvln.core.action import DiscreteAction
from uavvln.core.episode import EpisodeSpec, PointGoal
from uavvln.core.pose import Pose
from uavvln.core.state import UAVState
from uavvln.core.transform import ned_position_to_canonical, canonical_position_to_ned
from uavvln.env.dynamics import AirSimDynamicsBackend
from uavvln.env.renderer import UnrealRenderer
from uavvln.env.geometry import UnrealGeometry
from uavvln.core.observation import CameraSpec
from uavvln.benchmarks.aerialvln.dataset import episode_from_record
from uavvln.agents import Seq2SeqAgent, CMAAgent
from uavvln.controller import DiscreteController

class FakeAirSimClient:
    def __init__(self): self.pos = np.array([1., 2., -3.]); self.collided = False
    def reset(self): pass
    def simSetVehiclePose(self, pose, ignore_collision, vehicle_name=""):
        self.pos = np.array([pose.position.x_val, pose.position.y_val, pose.position.z_val])
    def getMultirotorState(self, vehicle_name=""):
        v = lambda: NS(x_val=0., y_val=0., z_val=0.)
        return NS(timestamp=2_000_000_000, kinematics_estimated=NS(
            position_val=NS(x_val=self.pos[0], y_val=self.pos[1], z_val=self.pos[2]),
            orientation=NS(x_val=0., y_val=0., z_val=0., w_val=1.),
            linear_velocity=v(), angular_velocity=v()))
    def moveByVelocityAsync(self, x, y, z, duration, vehicle_name=""):
        self.pos += np.array([x, y, z]) * duration; return NS(join=lambda: None)
    def simGetImages(self, requests, vehicle_name=""):
        return [NS(image_type=req.image_type,
                    image_data_uint8=bytes([7]) * (64 * 64 * 3),
                    image_data_float=[3.] * (64 * 64)) for req in requests]
    def simGetCollisionInfo(self, vehicle_name=""): return NS(has_collided=self.collided)

class Phase1Tests(unittest.TestCase):
    def test_coordinate_roundtrip(self):
        p = np.array([1., -2., 3.]); self.assertTrue(np.allclose(canonical_position_to_ned(ned_position_to_canonical(p)), p))

    def test_fake_airsim_pipeline(self):
        client = FakeAirSimClient(); dynamics = AirSimDynamicsBackend(client)
        state = dynamics.reset(UAVState(Pose([1, 2, 3])))
        self.assertTrue(np.allclose(state.pose.position, [1, 2, 3]))
        dynamics.step(DiscreteAction("forward"), .2)
        output = UnrealRenderer(client).render(CameraSpec(), state.pose, ["rgb", "depth"])
        self.assertEqual(output.rgb.shape, (64, 64, 3)); self.assertEqual(output.depth.shape, (64, 64))
        geometry = UnrealGeometry(client); self.assertFalse(geometry.collision(state.pose))
        client.collided = True; self.assertTrue(geometry.collision(state.pose))

    def test_vertical_action_uses_ned_sign(self):
        client = FakeAirSimClient(); dynamics = AirSimDynamicsBackend(client)
        dynamics.reset(UAVState(Pose.identity())); dynamics.step(DiscreteAction("ascend"), .2)
        self.assertLess(client.pos[2], 0.0)

    def test_adapters_and_agents(self):
        episode = episode_from_record({"id": "a", "scene": "s", "split": "val_unseen",
                                       "instruction": "fly", "start_position": [0, 0, 0], "goal_position": [1, 0, 0]})
        self.assertIsInstance(episode, EpisodeSpec); self.assertEqual(episode.metadata["split"], "val_unseen")
        action = Seq2SeqAgent().act(type("Obs", (), {"instruction": "fly"})())
        self.assertIsInstance(action, DiscreteAction); self.assertIsInstance(CMAAgent().act(None), DiscreteAction)
        command = DiscreteController().convert(action, UAVState(Pose.identity()))
        self.assertEqual(command.velocity_ned.shape, (3,))

if __name__ == "__main__": unittest.main()
