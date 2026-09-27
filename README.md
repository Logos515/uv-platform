# UAV-VLN Unified Platform: Phase 0

Phase 0 establishes the simulator-independent protocol and proves a complete
episode with a deterministic kinematic backend:

`reset -> observe -> agent.act -> step -> evaluate`

The implementation uses the canonical platform frame (right-handed, Z-up,
metres, radians, `xyzw` quaternions). Public observations intentionally hide
ground-truth pose and goal information; evaluators receive that information
through `StepResult.privileged_state`.

## Run the smoke episode

```bash
cd /data1/xuyihao/project/uv-platform
PYTHONPATH=. python -m uavvln.cli smoke
```

The package can also be installed with `pip install -e .`, which exposes the
`uavvln smoke` command.

## Run tests

```bash
PYTHONPATH=. python -m pytest -q
```

Phase 0 components are deliberately small and dependency-light:

- `uavvln.core`: Pose, state, observation, action, episode, task and capability contracts.
- `uavvln.env.dynamics.KinematicBackend`: deterministic point-mass dynamics.
- `uavvln.env.renderer.DummyRenderer`: shape-correct simulator-free RGB output.
- `uavvln.benchmarks.ToyBenchmark`: one navigation episode.
- `uavvln.agents.RandomAgent`: minimal protocol-compatible agent.
- `uavvln.runtime.Runner` and `uavvln.evaluation`: complete rollout and diagnostics.
