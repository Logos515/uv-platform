from uavvln.core.episode import EpisodeSpec, PointGoal
from uavvln.core.pose import Pose
from uavvln.core.task import NavigationTask

class ToyBenchmark:
    name = "toy"
    def __init__(self):
        self.task = NavigationTask(max_steps=50)
    def episodes(self, split="test"):
        return [EpisodeSpec("toy-0", "empty", "Fly to the red marker", Pose.identity(),
                            PointGoal((2.0, 0.0, 0.0), success_radius=0.2),
                            metadata={"max_steps": self.task.max_steps, "split": split})]
    def task_spec(self): return self.task
    def capabilities(self): return {"instruction", "rgb", "discrete", "velocity"}
