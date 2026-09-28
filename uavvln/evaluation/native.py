"""Native AerialVLN-style metrics over completed rollouts."""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class NativeMetrics:
    success_rate: float
    spl: float
    episodes: int
    successes: int

def compute_native_metrics(results, reference_lengths=None):
    results = list(results); n = len(results)
    if not n: return NativeMetrics(0.0, 0.0, 0, 0)
    successes = sum(bool(r.success) for r in results)
    spl_values = []
    for i, result in enumerate(results):
        reference = (reference_lengths or {}).get(result.episode_id, result.steps)
        ratio = min(1.0, float(reference) / max(1, result.steps))
        spl_values.append(ratio if result.success else 0.0)
    return NativeMetrics(successes / n, sum(spl_values) / n, n, successes)
