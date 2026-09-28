from pathlib import Path
from .dataset import load_episodes
from uavvln.core.task import NavigationTask

class AerialVLNBenchmark:
    name = "aerialvln"
    def __init__(self, dataset=None, task=None):
        self.dataset = dataset; self.task = task or NavigationTask(max_steps=200)
    def episodes(self, split="val_unseen"):
        if self.dataset is None: return []
        if isinstance(self.dataset, (str, Path)): return load_episodes(self.dataset, split)
        return [episode for episode in self.dataset if episode.metadata.get("split", split) == split]
    def task_spec(self): return self.task
    def capabilities(self): return {"instruction", "rgb", "discrete"}
