from uavvln.evaluation.evaluator import evaluate

class Runner:
    """Small protocol runner used by Phase 0 and reusable by later backends."""
    def __init__(self, benchmark, environment, agent):
        self.benchmark = benchmark
        self.environment = environment
        self.agent = agent

    def evaluate(self, split="test"):
        return evaluate(self.benchmark, self.environment, self.agent, split)
