# UAV-VLN Unified Platform: Phase 0–1

Phase 0 establishes the simulator-independent protocol and proves a complete
episode with a deterministic kinematic backend. Phase 1 adds optional AirSim /
Unreal adapters, AerialVLN episode conversion, discrete control, Seq2Seq/CMA
agent adapters, SensorSuite v0.1 and native SR/SPL diagnostics:

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

## Phase 1 adapters

`AirSimDynamicsBackend`, `UnrealRenderer` and `UnrealGeometry` accept an
injected AirSim client, which keeps unit tests independent of a running Unreal
process. With the AirSim SDK installed, omit the client and the adapters create
the normal `MultirotorClient` themselves. NED conversion is confined to
`uavvln.core.transform` and the AirSim backend.

AerialVLN records can be JSON or JSONL. The adapter accepts `episode_id`/`id`,
`scene_id`/`scene`, `start_pose` or `start_position`, and `goal` or
`goal_position` fields:

```python
from uavvln.benchmarks.aerialvln import AerialVLNBenchmark
benchmark = AerialVLNBenchmark("episodes.json")
episodes = benchmark.episodes("val_unseen")
```

The Phase 1 CLI command is available even without a configured dataset (it
reports that no episodes are configured):

```bash
uavvln eval benchmark=aerialvln agent=cma split=val_unseen
```

## Validation in `uavagent`

```bash
conda run -n uavagent python -m unittest discover -s tests -p 'test*_unittest.py' -v
conda run -n uavagent python -m uavvln.cli smoke
```

The fake AirSim regression suite covers coordinate conversion, state reset and
step, RGB/depth decoding, collision queries, AerialVLN conversion, discrete
control, and both agent adapters without requiring a simulator process.
