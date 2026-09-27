from uavvln.core.action import DiscreteAction

class RandomAgent:
    def __init__(self, seed=0): self.seed = seed; self.steps = 0
    def reset(self, task_context=None): self.steps = 0
    def act(self, observation):
        self.steps += 1
        return DiscreteAction("forward", magnitude=0.5)
