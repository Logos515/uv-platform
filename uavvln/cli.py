import argparse
import sys
from .agents import RandomAgent
from .benchmarks import ToyBenchmark
from .env.dynamics import KinematicBackend
from .env.environment import UAVEnvironment
from .env.geometry import NoGeometry
from .env.renderer import DummyRenderer
from .evaluation.evaluator import evaluate

def main(argv=None):
    # Accept both argparse flags and the roadmap's ``key=value`` invocation.
    argv = list(argv) if argv is not None else sys.argv[1:]
    if argv and any("=" in item for item in argv):
        normalized = []
        for item in argv:
            if "=" in item and not item.startswith("--"):
                key, value = item.split("=", 1); normalized.extend([f"--{key}", value])
            else: normalized.append(item)
        argv = normalized
    parser = argparse.ArgumentParser(description="Run a simulator-free UAV-VLN Phase 0 episode")
    parser.add_argument("command", choices=["smoke", "eval"], nargs="?", default="smoke")
    parser.add_argument("--benchmark", default="toy")
    parser.add_argument("--agent", default="random")
    parser.add_argument("--split", default="test")
    args = parser.parse_args(argv)
    if args.benchmark != "toy" or args.agent not in ("random",):
        # Phase 1 adapters are selectable even when no external dataset is supplied.
        from .benchmarks import AerialVLNBenchmark
        from .agents import CMAAgent, Seq2SeqAgent
        benchmark = AerialVLNBenchmark()
        agent = CMAAgent() if args.agent == "cma" else Seq2SeqAgent()
        if not benchmark.episodes(args.split):
            print(f"{args.benchmark}: no dataset configured for split={args.split}")
            return 0
    else:
        benchmark = ToyBenchmark(); agent = RandomAgent()
    env = UAVEnvironment(KinematicBackend(), DummyRenderer(), NoGeometry())
    results = evaluate(benchmark, env, agent, args.split)
    for result in results:
        print(f"{result.episode_id}: success={result.success} steps={result.steps} distance={result.final_distance:.3f}")
    return 0 if all(r.success for r in results) else 1

if __name__ == "__main__": main()
