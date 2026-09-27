import argparse
from .agents import RandomAgent
from .benchmarks import ToyBenchmark
from .env.dynamics import KinematicBackend
from .env.environment import UAVEnvironment
from .env.geometry import NoGeometry
from .env.renderer import DummyRenderer
from .evaluation.evaluator import evaluate

def main(argv=None):
    parser = argparse.ArgumentParser(description="Run a simulator-free UAV-VLN Phase 0 episode")
    parser.add_argument("command", choices=["smoke", "eval"], nargs="?", default="smoke")
    parser.add_argument("--split", default="test")
    args = parser.parse_args(argv)
    benchmark = ToyBenchmark()
    env = UAVEnvironment(KinematicBackend(), DummyRenderer(), NoGeometry())
    results = evaluate(benchmark, env, RandomAgent(), args.split)
    for result in results:
        print(f"{result.episode_id}: success={result.success} steps={result.steps} distance={result.final_distance:.3f}")
    return 0 if all(r.success for r in results) else 1

if __name__ == "__main__": main()
