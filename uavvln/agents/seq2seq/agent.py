"""Protocol-only Seq2Seq adapter.

The optional model can implement ``predict(observation, instruction)``. The
fallback is deterministic and is useful for integration/regression tests.
"""
from uavvln.core.action import DiscreteAction

class Seq2SeqAgent:
    def __init__(self, model=None): self.model = model; self.step_count = 0
    def reset(self, task_context=None): self.step_count = 0
    def act(self, observation):
        self.step_count += 1
        if self.model is not None:
            action = self.model.predict(observation, observation.instruction)
            if not isinstance(action, DiscreteAction): raise TypeError("Seq2Seq model must return DiscreteAction")
            return action
        return DiscreteAction("forward", magnitude=1.0)
