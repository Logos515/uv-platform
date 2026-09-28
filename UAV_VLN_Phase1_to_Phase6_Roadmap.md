# UAV-VLN 大一统平台 Phase 1–6 实施路线图

> 前提：Phase 0 已完成，即 `Core Spec + KinematicBackend + DummyRenderer + ToyBenchmark + RandomAgent + Runner` 已经能够跑通完整的 `reset → observe → act → step → evaluate` 流程。
>
> 本路线图延续原始框架的核心原则：**统一协议，而不是统一模拟器**；不同 benchmark、agent、simulator 通过稳定的协议与适配层组合，而不是彼此直接依赖。

---

## 0. 总体目标

Phase 1–6 的目标不是单纯“接更多 benchmark”，而是逐步验证六类核心能力：

| Phase | 核心验证问题 |
|---|---|
| Phase 1 | 统一协议能否承载真实 AirSim benchmark？ |
| Phase 2 | 一个 benchmark 能否在多个环境 backend 上运行？ |
| Phase 3 | Renderer / Geometry / Dynamics 是否真的可以解耦？ |
| Phase 4 | 协议能否支持 multi-view、continuous action、trajectory？ |
| Phase 5 | 能否建立严格的 Native / Unified 双评测体系？ |
| Phase 6 | 能否扩展到 GTA / Habitat / PX4 / VLA，并形成插件生态？ |

最终希望平台稳定形成：

```text
Experiment
=
Agent
× Task
× Benchmark
× Scene
× Dynamics
× Renderer
× Geometry
× Sensors
× Controller
× Protocol
```

---

# Phase 1：AirSim + AerialVLN + Seq2Seq / CMA

## 1.1 阶段目标

Phase 1 的目标是把 Phase 0 的“玩具闭环”升级成第一个真实 UAV-VLN pipeline：

```text
AerialVLN
    ↓
AirSim Environment
    ↓
Seq2Seq / CMA Agent
    ↓
Native Evaluation
```

这一阶段最重要的不是性能，而是证明：

1. Core Protocol 能支持真实 benchmark；
2. Agent 不直接依赖 AirSim；
3. Benchmark 不直接控制 simulator；
4. 原 benchmark 可以通过 adapter 接入；
5. 可以复现至少一条官方 evaluation pipeline。

---

## 1.2 固化 Core Protocol v0.1

在接 AirSim 之前，把 Phase 0 中已经使用过的核心类型整理成正式接口，但此时只标记为：

```text
Protocol v0.1 — provisional
```

不要宣布永久冻结。

建议至少包含：

```text
core/
├── pose.py
├── transform.py
├── state.py
├── observation.py
├── action.py
├── episode.py
├── task.py
├── capability.py
├── coordinate.py
└── protocol_version.py
```

### 必须明确的坐标约定

建议统一：

```text
World:
    right-handed
    Z-up
    meters

Angles:
    radians

Quaternion:
    xyzw
```

除此之外必须明确：

```text
T_world_body 的定义
body frame 的 forward/right/up
camera frame
camera optical frame
camera extrinsic 的方向
depth 的定义
timestamp 的定义
```

禁止仅用一个模糊的 `frame: str` 来解决所有坐标问题。

建议增加：

```python
@dataclass
class Transform:
    translation: np.ndarray
    quaternion_xyzw: np.ndarray
    parent_frame: str
    child_frame: str
```

---

## 1.3 实现 AirSimDynamicsBackend

新增：

```text
env/dynamics/airsim.py
```

接口至少支持：

```python
class AirSimDynamicsBackend(DynamicsBackend):

    def reset(self, initial_state):
        ...

    def step(self, control, dt):
        ...

    def get_state(self) -> UAVState:
        ...

    def set_state(self, state):
        ...

    def capabilities(self) -> DynamicsCapabilities:
        ...
```

所有 AirSim NED → Platform Z-up 的转换只能发生在 backend / coordinate adapter 中。

Agent、Benchmark、Trainer 中禁止出现：

```python
airsim.Vector3r
airsim.Pose
airsim.YawMode
```

---

## 1.4 实现 UnrealRenderer

建议把 AirSim 中的图像获取逻辑也包装成独立 Renderer：

```text
env/renderer/unreal.py
```

实现：

```python
render(
    camera: CameraSpec,
    pose: Pose,
    modalities: list[str]
) -> RenderOutput
```

Phase 1 最低支持：

```text
RGB
Depth
```

如果 AerialVLN 原始设置需要其他 modality，再增加对应字段。

---

## 1.5 实现 UnrealGeometry

增加：

```text
env/geometry/unreal.py
```

最少支持：

```text
collision
distance query
```

如果 AirSim / Unreal API 可以直接提供碰撞信息，可以优先通过 simulator 原生接口实现。

这一阶段不需要做复杂 mesh export。

---

## 1.6 完成 SensorSuite v0.1

实现：

```text
env/sensors/
├── camera.py
├── depth.py
└── pose.py
```

Agent 最终只接收：

```python
Observation
```

而不能主动向 AirSim 请求图像。

建议开始引入：

```python
@dataclass
class ObservationSpec:
    modalities: ...
    camera_specs: ...
    history_length: ...
```

此时至少描述：

```text
resolution
FOV / intrinsics
camera pose
dtype
visibility
```

---

## 1.7 编写 AerialVLN Benchmark Adapter

增加：

```text
benchmarks/aerialvln/
├── benchmark.py
├── dataset.py
├── task.py
├── episode_adapter.py
├── evaluator.py
└── config.yaml
```

完成：

```text
原始 episode
    ↓
EpisodeSpec

原始任务定义
    ↓
TaskSpec

原始 evaluator
    ↓
NativeEvaluator
```

优先保留官方逻辑，不要重新发明一套“看起来等价”的 evaluator。

---

## 1.8 实现 DiscreteAction

Phase 1 重点支持 AerialVLN 所需的离散动作。

例如：

```python
@dataclass
class DiscreteAction:
    name: Literal[
        "forward",
        "turn_left",
        "turn_right",
        "ascend",
        "descend",
        "stop",
    ]
```

然后通过：

```text
DiscreteAction
    ↓
DiscreteControllerAdapter
    ↓
AirSim native command
```

执行。

---

## 1.9 接入 Seq2Seq

增加：

```text
agents/seq2seq/
├── agent.py
├── model.py
├── preprocess.py
└── config.yaml
```

统一 Agent 接口：

```python
agent.reset(task_context)
action = agent.act(observation)
```

Seq2Seq 代码中不得出现：

```text
AirSim
AerialVLN simulator client
```

可以知道：

```text
TaskSpec
ObservationSpec
ActionSpec
```

---

## 1.10 接入 CMA

新增：

```text
agents/cma/
```

目标不是重新训练出最佳结果，而是证明第二种真实 VLN agent 也能通过相同协议运行。

---

## 1.11 建立 Native Evaluation v0.1

Phase 1 首先实现：

```text
evaluation/native.py
```

要求尽可能保留：

```text
原 split
原 sensor config
原 action semantics
原 success threshold
原 evaluator
```

输出至少包括：

```text
SR
SPL
原 benchmark 官方指标
```

---

## 1.12 Phase 1 测试

### Unit Test

至少覆盖：

```text
AirSim ↔ canonical coordinate conversion
quaternion conversion
depth conversion
camera extrinsics
DiscreteAction conversion
EpisodeSpec conversion
```

### Integration Test

必须能自动执行：

```text
load episode
reset AirSim
observe
agent.act
controller.convert
environment.step
evaluate
```

### Regression Test

固定一个简单 episode：

```text
seed 固定
start pose 固定
action sequence 固定
```

确保每次执行轨迹差异在允许范围内。

---

## 1.13 Phase 1 交付物

```text
AirSimDynamicsBackend
UnrealRenderer
UnrealGeometry
AerialVLN adapter
Seq2Seq adapter
CMA adapter
DiscreteController
NativeEvaluator
Core Protocol v0.1
```

---

## 1.14 Phase 1 退出标准

只有同时满足下面条件才能进入 Phase 2：

- [ ] AerialVLN episode 可以通过统一 Runner 执行
- [ ] Seq2Seq 可以运行
- [ ] CMA 可以运行
- [ ] Agent 中不存在 AirSim API
- [ ] Benchmark 中不存在直接 AirSim 控制逻辑
- [ ] 坐标转换全部集中在 adapter/backend
- [ ] Native evaluator 可以生成与官方定义一致的指标
- [ ] 至少有一个固定 episode regression test
- [ ] CLI 可以运行：

```bash
uavvln eval \
    benchmark=aerialvln \
    agent=cma \
    split=val_unseen
```

---

# Phase 2：OpenFly UE / AirSim，多环境组合

## 2.1 阶段目标

Phase 2 需要第一次真正验证：

> Benchmark ≠ Simulator。

目标结构：

```text
OpenFlyBenchmark
       │
       ├── Environment A
       │      Dynamics = AirSim
       │      Renderer = Unreal
       │      Geometry = Unreal
       │
       └── Environment B
              Dynamics = Kinematic
              Renderer = Unreal
              Geometry = Unreal
```

Agent 不应该知道自己运行在哪一种环境组合中。

---

## 2.2 引入 SceneSpec

新增：

```text
core/scene.py
```

建议：

```python
@dataclass
class SceneSpec:
    scene_id: str
    world_frame: str
    bounds: Bounds
    metadata: dict
```

---

## 2.3 引入 SceneBundle / SceneBinding

这是 Phase 2 最重要的新抽象之一。

```python
@dataclass
class SceneBundle:
    scene_id: str

    render_asset: AssetRef | None
    geometry_asset: AssetRef | None

    render_to_world: Transform
    geometry_to_world: Transform

    bounds: Bounds

    version: str
    checksum: str
```

目的：

```text
Renderer
Geometry
Dynamics
```

不能仅仅因为名字里 scene_id 相同就默认它们处于同一世界。

必须通过 SceneBinding 显式证明：

```text
Render Frame
     ↓
Canonical World
     ↑
Geometry Frame
```

---

## 2.4 重构 UAVEnvironment

建议正式形成：

```python
class UAVEnvironment:

    scene: SceneBundle

    dynamics: DynamicsBackend
    renderer: RendererBackend
    geometry: GeometryBackend
    sensors: SensorSuite
```

reset 流程建议统一成：

```text
load scene
→ reset dynamics
→ sync renderer
→ sync geometry
→ reset sensors
→ return observation
```

---

## 2.5 OpenFly Benchmark Adapter

新增：

```text
benchmarks/openfly/
```

包括：

```text
episode parser
task spec
goal spec
environment spec
native evaluator
```

不要把 OpenFly 特有逻辑直接写进 Environment Core。

---

## 2.6 ControllerAdapter 正式化

建立：

```text
controller/
├── base.py
├── discrete.py
├── waypoint.py
└── velocity.py
```

并规定：

```text
AgentAction
    ↓
ControllerAdapter
    ↓
ControlCommand
    ↓
DynamicsBackend
```

Controller config 必须成为实验配置的一部分。

---

## 2.7 CapabilityResolver v0.1

实现：

```text
AgentSpec
× BenchmarkSpec
× EnvironmentCapabilities
↓
CompatibilityReport
```

不要只返回 bool。

建议：

```python
@dataclass
class CompatibilityReport:
    status: CompatibilityStatus
    adapters: list[str]
    semantic_changes: list[str]
    warnings: list[str]
    reasons: list[str]
```

状态建议至少：

```text
NATIVE
LOSSLESS_ADAPTABLE
PROTOCOL_CHANGING
INCOMPATIBLE
```

其中：

```text
PROTOCOL_CHANGING
```

默认不能进入正式 benchmark evaluation。

---

## 2.8 配置系统升级

支持组合式环境配置：

```yaml
environment:
  dynamics:
    backend: airsim

  renderer:
    backend: unreal

  geometry:
    backend: unreal
```

Runner 不应该包含：

```python
if benchmark == "openfly":
    ...
```

---

## 2.9 Phase 2 测试

重点增加：

```text
scene reset consistency
same start pose across backends
sensor pose consistency
controller semantics
capability resolution
backend substitution
```

至少设计一个测试：

```text
同一个 OpenFly episode
同一个 Agent
同一个 Action sequence

AirSim dynamics
vs
Kinematic dynamics
```

验证平台层不会崩溃，并明确记录行为差异。

---

## 2.10 Phase 2 交付物

```text
OpenFlyBenchmark
SceneSpec
SceneBundle / SceneBinding
ControllerAdapter
CapabilityResolver v0.1
Composable Environment
OpenFly UE/AirSim execution pipeline
```

---

## 2.11 Phase 2 退出标准

- [ ] OpenFly 可以通过统一 Runner 执行
- [ ] 同一个 benchmark 可以切换至少两种 dynamics 配置
- [ ] Agent 无需修改
- [ ] Scene / coordinate alignment 有显式配置
- [ ] Controller 配置进入 experiment config
- [ ] CompatibilityResolver 可以提前报告不兼容组合
- [ ] Core / Trainer 中没有 benchmark-specific if/else

---

# Phase 3：3DGS Renderer + Mesh Geometry

## 3.1 阶段目标

Phase 3 是整个架构最重要的验证阶段之一。

需要证明：

```text
Dynamics
Renderer
Geometry
```

确实可以来自不同实现。

目标组合：

```text
Dynamics = Kinematic / AirSim
Renderer = Gaussian
Geometry = TriangleMesh
```

---

## 3.2 实现 GaussianRenderer

新增：

```text
env/renderer/gaussian.py
```

统一接口：

```python
render(camera, pose, modalities)
```

最低支持：

```text
RGB
```

如果 3DGS 实现支持 depth，可以作为 optional capability 暴露，不要默认所有 Gaussian renderer 都支持可靠 depth。

---

## 3.3 实现 TriangleMeshGeometry

新增：

```text
env/geometry/mesh.py
```

最低支持：

```text
collision
raycast
distance_to_obstacle
```

优先保证正确性，再优化速度。

---

## 3.4 Scene Registration

Phase 3 必须提供明确的 3DGS ↔ Mesh 空间注册流程。

每个 SceneBundle 至少记录：

```text
render_to_world
geometry_to_world
scale
bounds
asset version
asset checksum
```

建议提供工具：

```bash
uavvln tools validate-scene scene=xxx
```

输出：

```text
coordinate alignment
scale consistency
bounds overlap
camera reprojection consistency
sample point consistency
```

---

## 3.5 Render / Geometry 一致性测试

这是 Phase 3 必须增加的专项测试。

例如：

### Camera Pose Test

在已知位置放置相机：

```text
Renderer 中看到墙
Geometry raycast 也应该在相同方向检测到墙
```

### Collision Consistency Test

采样若干位置：

```text
mesh 判断 occupied
```

检查 Gaussian view 是否明显位于墙体内部或错误区域。

### Landmark Alignment Test

使用少量人工标记 landmark：

```text
3DGS landmark
↔ mesh landmark
```

计算空间误差。

---

## 3.6 Renderer Capability

正式支持：

```python
RendererCapabilities(
    rgb=True,
    depth=False,
    semantic=False,
    differentiable=False,
)
```

不要因为统一接口存在，就假设所有 renderer 能返回所有 modality。

---

## 3.7 Headless 支持

Phase 3 建议开始确保：

```text
Gaussian renderer
Kinematic backend
Mesh geometry
```

能够 headless 运行。

这对后续服务器 evaluation 非常重要。

---

## 3.8 ReplayRenderer

建议在这一阶段实现：

```text
env/renderer/replay.py
```

它可以从记录的数据中返回 observation。

用途：

```text
debug
unit test
agent-only benchmark
offline evaluation
reproducibility
```

---

## 3.9 Phase 3 交付物

```text
GaussianRenderer
TriangleMeshGeometry
Scene registration pipeline
scene validator
ReplayRenderer
renderer capability contract
3DGS + Mesh + Kinematic demo
```

---

## 3.10 Phase 3 退出标准

- [ ] GaussianRenderer 可通过统一 Renderer API 使用
- [ ] Mesh geometry 支持 collision / raycast
- [ ] 3DGS 与 mesh 有明确空间注册
- [ ] SceneBundle 记录版本和 checksum
- [ ] 至少有一套自动化 alignment test
- [ ] Kinematic + Gaussian + Mesh 可以跑完整 episode
- [ ] Agent 代码无需针对 3DGS 修改

---

# Phase 4：TravelUAV + Continuous Trajectory

## 4.1 阶段目标

Phase 4 重点压测之前偏离散的协议。

需要支持：

```text
multi-view observation
continuous action
trajectory action
6DoF / richer pose
history
MLLM / hierarchical policy
```

---

## 4.2 TravelUAV Benchmark Adapter

新增：

```text
benchmarks/traveluav/
```

统一转换：

```text
dataset → EpisodeSpec
task → TaskSpec
goal → GoalSpec
trajectory → Trajectory
```

---

## 4.3 ObservationSpec v0.2

正式支持多相机：

```text
front
left
right
rear
down
```

每一个 camera 都应拥有独立：

```text
intrinsics
extrinsics
resolution
modality support
```

而不是仅仅：

```python
rgb["front"]
```

---

## 4.4 Sensor History

增加：

```text
HistoryBuffer
```

建议不要把 history 隐含塞进 Agent。

平台应允许声明：

```yaml
observation:
  history:
    length: 8
    stride: 1
```

这样 NaVid / Video-VLM 类方法可以通过统一机制获取 temporal context。

---

## 4.5 TrajectoryAction

正式实现：

```python
@dataclass
class TrajectoryAction:
    poses: list[Pose]
    timestamps: list[float] | None
```

并明确：

```text
trajectory 是绝对坐标还是相对坐标
时间参数是否必须存在
yaw / attitude 是否必须存在
```

---

## 4.6 ActionChunk

为后续 VLA 提前加入：

```python
@dataclass
class ActionChunk:
    actions: np.ndarray
    dt: float | None
```

Phase 4 不一定必须训练 VLA，但协议需要开始经受 chunk action 的测试。

---

## 4.7 ExecutionSpec / Clock

这是 Phase 4 必须正式加入的基础设施。

新增：

```text
core/execution.py
env/clock.py
```

建议：

```python
@dataclass
class ExecutionSpec:
    physics_hz: float | None
    control_hz: float
    observation_hz: float
    action_horizon: float | None
```

必须回答：

```text
一次 env.step() 到底推进多少时间？
trajectory action 什么时候执行完？
sensor 是同步还是异步？
controller 运行频率是多少？
```

---

## 4.8 WaypointController / TrajectoryController

增加：

```text
controller/trajectory.py
```

统一：

```text
TrajectoryAction
→ TrajectoryController
→ velocity / pose / native command
```

必须记录 Controller config。

例如：

```yaml
controller:
  name: trajectory
  frequency: 20
  position_tolerance: 0.2
  yaw_tolerance: 0.1
```

---

## 4.9 TravelUAV Agent Adapter

将 TravelUAV 方法封装进：

```text
agents/traveluav/
```

禁止其直接控制 simulator。

如果原代码强耦合 simulator，则把：

```text
model logic
controller logic
simulator logic
```

拆开。

---

## 4.10 Phase 4 测试

重点：

```text
multi-view ordering
camera calibration
history sampling
continuous action range
trajectory execution
control frequency
step time semantics
trajectory termination
```

必须增加：

```text
same trajectory + same initial state
→ Kinematic backend deterministic replay
```

作为 regression test。

---

## 4.11 Phase 4 交付物

```text
TravelUAV benchmark adapter
TravelUAV agent adapter
Multi-view ObservationSpec
HistoryBuffer
TrajectoryAction
ActionChunk
ExecutionSpec
Clock
TrajectoryController
```

---

## 4.12 Phase 4 退出标准

- [ ] 5-view RGB 可通过统一 observation 获取
- [ ] continuous / trajectory action 可执行
- [ ] `env.step()` 时间语义明确
- [ ] controller frequency 明确
- [ ] TravelUAV agent 不依赖 simulator API
- [ ] Kinematic backend 可 deterministic replay
- [ ] AerialVLN / OpenFly 没有因协议升级而被破坏

---

# Phase 5：Native / Unified Evaluation

## 5.1 阶段目标

Phase 5 开始从“工程平台”转向“研究平台”。

需要建立：

```text
Native Track
+
Unified Track
+
Common Diagnostics
```

并开始真正进行 cross-benchmark experiment。

---

## 5.2 Native Track

每个 benchmark 保留：

```text
原 observation protocol
原 action protocol
原 success condition
原 evaluator
原 metrics
原 dataset split
```

平台只负责统一运行，不强行统一 benchmark 语义。

建议：

```text
evaluation/native/
├── aerialvln.py
├── openfly.py
└── traveluav.py
```

---

## 5.3 Unified Track

定义平台统一协议，例如第一版可以选择：

```text
Observation:
    front RGB
    instruction
    optional history

Forbidden:
    GT pose
    semantic map
    privileged goal coordinates

Action:
    4-DoF waypoint

Execution:
    fixed control semantics

Evaluation:
    common diagnostics
```

注意：

> Unified Track 的目标是统一实验协议，而不是声明不同 benchmark 的 SR 可以直接比较任务难度。

---

## 5.4 Common Diagnostics

统一记录：

```text
final_distance
min_goal_distance
trajectory_length
flight_time
collision_count
collision_duration
normalized_progress
energy_proxy
inference_latency
```

需要给每个 metric 明确：

```text
单位
计算公式
采样频率
缺失值策略
```

---

## 5.5 Privileged State Enforcement

Phase 5 建议把：

```text
Agent
Environment
Evaluator
```

的边界进一步强化。

最低限度通过不同对象隔离：

```text
Observation
PrivilegedState
```

更严格的 evaluation 可进一步发展为：

```text
Agent Process
Environment Process
Evaluator Process
```

正式 leaderboard 之前建议实现进程级隔离。

---

## 5.6 RunManifest

每次实验必须自动产生：

```text
run_manifest.json
```

至少记录：

```text
experiment id
git commit
protocol version
benchmark version
dataset version
scene version
asset checksums
agent config
checkpoint hash
controller config
backend versions
seed
hardware info
start/end time
```

这是保证 benchmark 可复现的关键。

---

## 5.7 Recorder / Replay

增加：

```text
runtime/recorder.py
```

建议每个 episode 可选择记录：

```text
observation metadata
action
state
privileged state
metrics
timestamps
collision events
```

图像可以按配置决定是否完整保存。

---

## 5.8 Compatibility Matrix

自动生成：

```text
Agent × Benchmark × Protocol
```

兼容性矩阵。

例如：

| Agent | AerialVLN Native | OpenFly Native | TravelUAV Native | Unified |
|---|---:|---:|---:|---:|
| Seq2Seq | NATIVE | ... | ... | ... |
| CMA | NATIVE | ... | ... | ... |
| NaVid | ... | ... | ... | ... |
| TravelUAV | ... | ... | NATIVE | ... |

状态只描述协议兼容性，不描述模型性能优劣。

---

## 5.9 Cross-Benchmark Evaluation

开始设计正式实验：

### Experiment A

```text
Train on AerialVLN
Evaluate on AerialVLN / OpenFly / TravelUAV Unified Track
```

### Experiment B

```text
Same Agent
Same ObservationSpec
Same ActionSpec
Different Renderer
```

### Experiment C

```text
Same Agent
Same Benchmark
AirSim vs Gaussian environment
```

这些实验才能真正验证平台研究价值。

---

## 5.10 Protocol Versioning

在 Phase 5 正式引入：

```text
Protocol v1
```

例如：

```text
uavvln-protocol: 1.0
```

以后 breaking change 必须升级 major version。

---

## 5.11 Phase 5 交付物

```text
Native Track
Unified Track
CommonDiagnostics
RunManifest
Recorder
Replay support
Compatibility Matrix
Protocol v1
Cross-benchmark experiment scripts
```

---

## 5.12 Phase 5 退出标准

- [ ] 三个 benchmark 都支持 Native Track
- [ ] 至少两个 benchmark 支持相同 Unified Track
- [ ] privileged information 不会进入 Agent observation
- [ ] 每个 run 可生成完整 manifest
- [ ] 所有 common metric 定义固定
- [ ] experiment 可通过 config 完整复现
- [ ] 已完成至少一组 cross-benchmark 实验
- [ ] Protocol v1 可以冻结

---

# Phase 6：GTA / Habitat / PX4 / VLA / 插件生态

## 6.1 阶段目标

Phase 6 不再主要验证核心抽象，而是验证：

> 平台是否具备长期扩展能力。

重点扩展：

```text
GTA
Habitat
PX4
VLA
distributed runtime
plugin ecosystem
```

---

# 6.2 GTA Backend

建议分别实现：

```text
GTAVRenderer
GTAVDynamicsBackend
GTAVGeometry / ProxyGeometry
```

不要尝试：

```text
GTA → Unreal → AirSim
```

而是直接实现统一 backend 接口。

如果 GTA geometry API 不完整，可以明确声明：

```text
GeometryCapabilities
```

中哪些功能不可用。

---

## 6.3 Habitat Backend

增加：

```text
HabitatRenderer
HabitatGeometry
HabitatDynamics / Kinematic integration
```

Habitat 的价值主要是验证：

```text
不同 simulator family
```

能否接入同一个 protocol。

---

## 6.4 PX4 Backend

新增：

```text
env/dynamics/px4.py
```

这是从“导航模拟平台”走向真实飞控接口的关键一步。

PX4 接入必须明确：

```text
control mode
offboard mode
coordinate conversion
control rate
timeout
failsafe
```

建议最初只用于：

```text
SITL
```

稳定后再考虑实机。

---

## 6.5 VLA Agent

正式支持：

```text
ActionChunk
```

典型流程：

```text
Observation history
    ↓
VLA
    ↓
ActionChunk
    ↓
ChunkController
    ↓
DynamicsBackend
```

需要支持：

```text
chunk horizon
replan frequency
early interruption
safety override
```

---

## 6.6 Runtime Process Isolation

逐步形成：

```text
Agent Process
Environment Process
Evaluator Process
```

目的：

```text
防 privileged information 泄漏
故障隔离
GPU 资源管理
leaderboard 安全性
```

---

## 6.7 Wire Protocol

如果需要跨进程 / 跨机器运行，开始定义：

```text
Core Python API
≠
Wire Protocol
```

需要解决：

```text
serialization
IPC
schema versioning
large image transfer
shared memory
timeout
error handling
process crash
```

不要直接把 Python dataclass 当长期 RPC 协议。

---

## 6.8 Distributed Evaluation

增加：

```text
runtime/distributed.py
```

目标支持：

```text
one experiment
→ many scenes
→ many workers
→ aggregated metrics
```

要求：

```text
episode deterministic assignment
seed isolation
retry policy
failure logging
result aggregation
```

---

## 6.9 Plugin Registry

平台正式从内置模块转为：

```text
core package
+
plugins
```

建议 registry 支持：

```text
benchmark
agent
dynamics backend
renderer backend
geometry backend
controller
trainer
evaluator
```

例如：

```python
@register_renderer("gaussian")
class GaussianRenderer(...):
    ...
```

---

## 6.10 Dependency Isolation

不要要求：

```bash
pip install uavvln
```

就安装所有大型依赖。

建议：

```text
uavvln-core
uavvln-air sim
uavvln-gaussian
uavvln-habitat
uavvln-px4
```

或者：

```bash
pip install uavvln[airsim]
pip install uavvln[gaussian]
```

重型 simulator 也可以采用独立环境 / service 方式运行。

---

## 6.11 Benchmark / Agent Plugin Template

提供模板：

```text
templates/
├── benchmark_plugin/
├── agent_plugin/
├── renderer_plugin/
└── dynamics_plugin/
```

一个新的 benchmark 最理想的接入流程应该是：

```text
实现 Benchmark interface
声明 CapabilitySpec
提供 config
注册 plugin
运行 compatibility test
```

而不是修改 Core。

---

## 6.12 CI / Compatibility Tests

建立自动测试矩阵：

```text
Core × Python versions
Core × benchmark adapters
Agent × observation spec
Backend × capability contract
```

重型 simulator 可以使用：

```text
mock test
nightly integration test
```

而不是所有 PR 都启动 Unreal / GTA。

---

## 6.13 Phase 6 交付物

```text
GTA backend
Habitat backend
PX4 SITL backend
VLA agent interface
ActionChunk controller
process isolation
wire protocol prototype
distributed evaluation
plugin registry
plugin templates
dependency isolation
CI compatibility matrix
```

---

## 6.14 Phase 6 退出标准

- [ ] 新增 backend 不需要修改 Core
- [ ] 新增 benchmark 不需要修改 Agent
- [ ] 新增 Agent 不需要修改 Environment
- [ ] GTA / Habitat / PX4 至少各有一条可运行 pipeline
- [ ] VLA 可通过 ActionChunk 运行
- [ ] 进程隔离 evaluation 可运行
- [ ] 插件具备独立依赖管理能力
- [ ] distributed evaluation 可聚合结果
- [ ] Protocol v1 保持向后兼容

---

# 七、建议的版本演化

推荐不要在 Phase 0 后立即冻结所有接口。

建议：

```text
Phase 0
    ↓
Protocol prototype

Phase 1
    ↓
Protocol v0.1

Phase 2
    ↓
Protocol v0.2

Phase 3
    ↓
Protocol v0.3

Phase 4
    ↓
Protocol v0.4

Phase 5
    ↓
Protocol v1.0

Phase 6
    ↓
Backward-compatible extension
```

原因是：

```text
AerialVLN
OpenFly
TravelUAV
3DGS
```

分别会暴露完全不同的协议问题。

只有这些正交 use case 都跑通以后，才适合真正冻结 v1。

---

# 八、每个 Phase 都必须遵守的架构纪律

整个 Phase 1–6 开发过程中持续检查：

```text
Agent 中禁止出现：
    AirSim
    Unreal
    GTA
    Habitat
    specific benchmark simulator API

Benchmark 中禁止直接控制：
    AirSim
    SIBR
    GTA native API

Core 中禁止出现：
    if benchmark == ...
    if simulator == ...

所有坐标转换：
    只能存在于 CoordinateAdapter / Backend

所有 simulator native action：
    只能存在于 DynamicsBackend / ControllerAdapter

所有 privileged state：
    只能进入 Evaluator / Debugger

所有 backend 差异：
    必须通过 CapabilitySpec 暴露
```

如果开始出现：

```python
if benchmark == "openfly":
    ...
elif benchmark == "aerialvln":
    ...
```

并且这些判断进入：

```text
Agent
Trainer
Core
```

说明 abstraction 已经开始泄漏，应优先重构。

---

# 九、建议的测试层级

从 Phase 1 开始，测试建议固定成四层。

## L1：Unit Tests

测试纯协议和数学逻辑：

```text
coordinate transform
quaternion
action conversion
metric
episode parser
```

## L2：Contract Tests

每个 Backend 都必须通过统一测试：

```text
reset
step
get_state
render
collision
capabilities
```

## L3：Integration Tests

运行：

```text
Benchmark
× Environment
× Agent
```

的小规模 episode。

## L4：Regression Tests

固定：

```text
scene
episode
seed
agent checkpoint
config
```

检查结果是否出现异常漂移。

---

# 十、推荐的最终目录

到 Phase 5–6，项目可以逐步演化成：

```text
uavvln/

├── core/
│   ├── pose.py
│   ├── transform.py
│   ├── state.py
│   ├── observation.py
│   ├── action.py
│   ├── episode.py
│   ├── task.py
│   ├── capability.py
│   ├── scene.py
│   ├── execution.py
│   └── protocol_version.py
│
├── env/
│   ├── environment.py
│   ├── clock.py
│   │
│   ├── dynamics/
│   │   ├── kinematic.py
│   │   ├── airsim.py
│   │   ├── gtav.py
│   │   └── px4.py
│   │
│   ├── renderer/
│   │   ├── unreal.py
│   │   ├── gaussian.py
│   │   ├── gtav.py
│   │   ├── habitat.py
│   │   └── replay.py
│   │
│   ├── geometry/
│   │   ├── mesh.py
│   │   ├── unreal.py
│   │   ├── occupancy.py
│   │   └── habitat.py
│   │
│   └── sensors/
│
├── controller/
│   ├── discrete.py
│   ├── waypoint.py
│   ├── velocity.py
│   ├── trajectory.py
│   └── action_chunk.py
│
├── benchmarks/
│   ├── aerialvln/
│   ├── openfly/
│   └── traveluav/
│
├── agents/
│   ├── seq2seq/
│   ├── cma/
│   ├── navid/
│   ├── traveluav/
│   └── vla/
│
├── trainers/
│
├── evaluation/
│   ├── native/
│   ├── unified.py
│   ├── metrics.py
│   └── diagnostics.py
│
├── registry/
│
├── runtime/
│   ├── runner.py
│   ├── rollout.py
│   ├── recorder.py
│   ├── manifest.py
│   ├── ipc.py
│   └── distributed.py
│
├── configs/
├── tools/
├── templates/
└── tests/
```

---

# 十一、Phase 1–6 的依赖关系

推荐严格按下面顺序推进：

```text
Phase 0
Core + Toy Pipeline
        │
        ▼
Phase 1
AirSim + AerialVLN
验证真实 simulator
        │
        ▼
Phase 2
OpenFly + Composable Env
验证 benchmark / simulator 解耦
        │
        ▼
Phase 3
3DGS + Mesh
验证 renderer / geometry 解耦
        │
        ▼
Phase 4
TravelUAV + Trajectory
验证 multi-view / continuous / time
        │
        ▼
Phase 5
Native + Unified
验证 cross-benchmark evaluation
        │
        ▼
Phase 6
GTA / Habitat / PX4 / VLA
扩展为插件生态
```

不建议跳过 Phase 2–4 直接做 Phase 5。

因为 Phase 5 的 Unified Protocol 是否合理，必须经过：

```text
discrete benchmark
multi-backend benchmark
3DGS environment
continuous trajectory benchmark
```

共同压测后才能确定。

---

# 十二、当前最优先的下一步

既然 Phase 0 已经完成，现在不要马上同时接 OpenFly、3DGS 和 TravelUAV。

下一步只做：

```text
1. Core Protocol v0.1 整理
2. AirSimDynamicsBackend
3. UnrealRenderer
4. AerialVLN Benchmark Adapter
5. DiscreteController
6. Seq2Seq
7. Native Evaluator
8. CMA
```

第一条 milestone 定义为：

```bash
uavvln eval \
    benchmark=aerialvln \
    agent=seq2seq \
    split=val_unseen
```

能够从统一 CLI 启动，并完成：

```text
load benchmark
→ resolve compatibility
→ construct environment
→ reset episode
→ observe
→ agent.act
→ controller
→ dynamics
→ evaluate
→ save metrics
```

当这条链路稳定之后，再进入 OpenFly。

---

# 十三、最终判断标准

Phase 1–6 是否成功，不应该以“接了多少项目”为判断标准。

真正的判断标准是：

```text
新增一个 Agent
是否只需要写 Agent plugin？

新增一个 Benchmark
是否只需要写 Benchmark plugin？

新增一个 Renderer
是否只需要实现 RendererBackend？

新增一个 Dynamics Backend
是否不会影响 Agent？

修改 simulator
是否不会修改 benchmark protocol？

运行一次实验
是否可以精确知道：
    用了什么协议？
    什么场景？
    什么 controller？
    什么 backend？
    什么 checkpoint？
    什么 seed？
```

当这些问题基本都能回答“是”时，这个平台才真正从：

```text
benchmark collection
```

变成：

```text
UAV-VLN Unified Protocol & Evaluation Platform
```
