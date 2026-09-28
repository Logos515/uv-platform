"""Protocol-only CMA adapter with an injectable predictor."""
from uavvln.core.action import DiscreteAction

class CMAAgent:
    def __init__(self, predictor=None): self.predictor = predictor; self.step_count = 0
    def reset(self, task_context=None): self.step_count = 0
    def act(self, observation):
        self.step_count += 1
        action = self.predictor(observation) if self.predictor else DiscreteAction("forward", 1.0)
        if not isinstance(action, DiscreteAction): raise TypeError("CMA predictor must return DiscreteAction")
        return action
