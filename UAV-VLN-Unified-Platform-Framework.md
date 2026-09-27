# UAV-VLN 大一统平台框架设计

建议把这个项目从一开始就定义为“协议统一平台”，而不是“统一仿真器平台”。核心思想是：

> 不要求 UE、AirSim、3DGS、GTA V、Habitat 变成同一种环境，而是让它们通过同一套 `Environment Protocol` 被 benchmark、训练代码和方法调用。

这样后续新增一个 simulator、benchmark 或方法时，都应该只是增加一个插件，而不是修改整个系统。

---

## 一、总体架构

我建议最终形成下面的结构：

```text
                         UAV-VLN Platform
                                │
                  ┌─────────────┴─────────────┐
                  │                           │
              Experiment                 Registry
                  │                           │
        Benchmark × Agent × Config            │
                  │                           │
                  └─────────────┬─────────────┘
                                │
                    Compatibility Resolver
                                │
               Observation / Action Contract
                                │
                    Unified Environment API
                                │
       ┌────────────────────────┼────────────────────────┐
       │                        │                        │
 DynamicsBackend         RendererBackend          GeometryBackend
       │                        │                        │
 ┌─────┼──────┐         ┌──────┼───────┐        ┌──────┼──────┐
AirSim Kinematic PX4     UE    3DGS    GTA      Mesh   SDF   Occupancy
       │                        │                        │
       └────────────────────────┼────────────────────────┘
                                │
                         Sensor System
                                │
                    RGB / Depth / Pose / IMU
                                │
                              Agent
                                │
                       Controller Adapter
                                │
                             Action
```

整个系统最好明确分成九层：

```text
Core Protocol
Environment
Benchmark
Agent
Controller
Training
Evaluation
Data
Experiment / Runtime
```

后面所有代码都围绕这九层建设。

---

## 二、最底层首先定义 Core Protocol

这是整个项目最重要的部分。

不要先写 AirSim adapter。

先定义平台内部唯一认可的数据表示。

例如：

```python
@dataclass
class Pose:
    position: np.ndarray       # x, y, z
    quaternion: np.ndarray     # x, y, z, w
    frame: str                 # canonical world frame


@dataclass
class UAVState:
    pose: Pose
    linear_velocity: np.ndarray
    angular_velocity: np.ndarray
    timestamp: float
```

这里必须规定一个平台级 canonical coordinate system。

我建议统一成：

```text
Right-handed
Z-up
meters
radians
quaternion: xyzw
```

无论 AirSim 原生是 NED，还是某个 3DGS 使用 COLMAP 坐标，都不能泄露到 Agent 层。

全部转换成：

```text
Platform Coordinate System
```

比如：

```text
AirSim NED
    ↓
AirSimCoordinateAdapter
    ↓
Canonical SE(3)

COLMAP
    ↓
GSCoordinateAdapter
    ↓
Canonical SE(3)
```

这是第一条硬规则：

> 除 backend 外，其余模块永远不能知道 AirSim / UE / GTA / COLMAP 的原始坐标约定。

---

## 三、Environment 不应该等于 Simulator

这是你们平台最关键的结构。

定义：

```python
class UAVEnvironment:
    dynamics: DynamicsBackend
    renderer: RendererBackend
    geometry: GeometryBackend
    sensors: SensorSuite
```

也就是说：

\[
Environment =
Dynamics
+
Renderer
+
Geometry
+
Sensors
\]

而不是：

```text
Environment = AirSim
```

### 3.1 DynamicsBackend

只负责：

> UAV 如何运动。

接口可以非常小：

```python
class DynamicsBackend:

    def reset(self, initial_state):
        ...

    def step(self, control, dt):
        ...

    def get_state(self) -> UAVState:
        ...

    def set_state(self, state):
        ...

    def capabilities(self):
        ...
```

初期实现：

```text
DynamicsBackend

├── KinematicBackend
├── AirSimDynamicsBackend
├── ProjectAirSimBackend
└── PX4Backend              # 后期
```

建议第一版一定自己实现一个：

```text
KinematicBackend
```

例如：

```python
x += vx * dt
y += vy * dt
z += vz * dt
yaw += yaw_rate * dt
```

因为这样可以不依赖任何大型 simulator 做单元测试。

---

## 四、RendererBackend

只负责：

> 给定 camera pose，返回视觉结果。

接口类似：

```python
class RendererBackend:

    def load_scene(self, scene_id):
        ...

    def render(
        self,
        camera: CameraSpec,
        pose: Pose,
        modalities: list[str]
    ) -> RenderOutput:
        ...
```

例如：

```python
@dataclass
class RenderOutput:
    rgb: Optional[np.ndarray]
    depth: Optional[np.ndarray]
    semantic: Optional[np.ndarray]
```

然后分别实现：

```text
RendererBackend

├── UnrealRenderer
├── GaussianRenderer
├── GTAVRenderer
├── HabitatRenderer
└── ReplayRenderer
```

这里就是你前面问到的 OpenFly 的核心。

### AirSim / UE

```text
Dynamics = AirSim
Renderer = Unreal
```

### 3DGS

可以：

```text
Dynamics = Kinematic / AirSim
Renderer = SIBR / Gaussian Splatting
```

### GTA V

可以：

```text
Dynamics = GTAV native / Kinematic
Renderer = GTA V
```

因此没有必要：

```text
GTA V → Unreal → AirSim
```

只需要：

```text
GTAVRenderer
```

实现统一接口。

---

## 五、GeometryBackend 要单独存在

这是非常容易被忽略的一层。

它负责：

```text
collision
raycast
distance query
occupancy
visibility
```

定义：

```python
class GeometryBackend:

    def collision(self, pose: Pose) -> bool:
        ...

    def raycast(self, origin, direction):
        ...

    def distance_to_obstacle(self, pose):
        ...
```

实现：

```text
GeometryBackend

├── UnrealMeshGeometry
├── TriangleMeshGeometry
├── OccupancyGridGeometry
├── SDFGeometry
└── NoGeometry
```

这样 3DGS 环境可以：

```text
GaussianRenderer
+
TriangleMeshGeometry
```

即：

```text
3DGS
   ↓
视觉

Mesh
   ↓
碰撞
```

而不是强迫 Gaussian 本身承担 collision。

---

## 六、Sensor 层再建立一层抽象

Agent 不应该直接调用：

```python
airsim.simGetImages()
```

而应该得到：

```text
Observation
```

例如：

```python
@dataclass
class Observation:

    rgb: dict[str, np.ndarray] | None
    depth: dict[str, np.ndarray] | None

    pose: Pose | None
    imu: IMUData | None
    gps: GPSData | None

    semantic_map: Any | None
    geographic_map: Any | None

    instruction: str | None
    assistant_message: str | None

    timestamp: float
```

多个 camera：

```text
rgb["front"]
rgb["left"]
rgb["right"]
rgb["rear"]
rgb["down"]
```

于是 TravelUAV：

```text
5-view RGB
5-view depth
pose
instruction
```

AerialVLN：

```text
front RGB
depth
instruction
```

NaVid：

```text
front RGB history
instruction
```

全部可以放进同一个结构。

注意：

> Observation 里字段可以为空，不是所有 benchmark 都必须提供全部 modality。

---

## 七、Public Observation 和 Privileged State 必须分开

这是 benchmark 公平性的核心。

设计：

```python
@dataclass
class EnvironmentState:
    public_observation: Observation
    privileged_state: PrivilegedState
```

例如：

```python
class PrivilegedState:
    gt_pose
    gt_goal
    collision_geometry
    shortest_path
    semantic_labels
```

流程必须是：

```text
Simulator
    │
    ├────────→ Observation ─────→ Agent
    │
    └────────→ PrivilegedState ─→ Evaluator
```

绝对不要：

```python
obs["goal_position"]
```

然后靠 Agent 自觉不用。

后续如果做 leaderboard，甚至可以：

```text
Agent Process
      │ IPC
Environment Process
      │
Evaluator Process
```

三者隔离。

---

## 八、ActionSpec 是另一个核心

绝对不要设计：

```python
action: np.ndarray
```

因为 UAV-VLN action 类型差异太大。

应该显式建模：

```text
AgentAction

├── DiscreteAction
├── ParameterizedAction
├── VelocityAction
├── WaypointAction
├── PoseAction
├── TrajectoryAction
└── ActionChunk
```

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

NaVid：

```python
@dataclass
class ParameterizedAction:
    action: str
    magnitude: float
```

TravelUAV：

```python
@dataclass
class TrajectoryAction:
    poses: list[Pose]
```

VLA：

```python
@dataclass
class ActionChunk:
    actions: np.ndarray   # [T, D]
```

这样统一的不是：

> 大家都输出相同 action。

而是：

> 大家都通过明确声明的 ActionSpec 输出动作。

---

## 九、ControllerAdapter

这一层负责解耦 Method 和 Simulator。

例如 Agent 输出：

```text
Waypoint(x, y, z, yaw)
```

AirSim 需要：

```text
velocity command
```

那么：

```text
WaypointAction
      ↓
WaypointController
      ↓
VelocityCommand
      ↓
AirSim
```

定义：

```python
class ControllerAdapter:

    def reset(self):
        ...

    def convert(
        self,
        agent_action,
        current_state
    ) -> ControlCommand:
        ...
```

于是：

```text
Agent
 ↓
abstract action
 ↓
ControllerAdapter
 ↓
native simulator command
```

这能解决你之前提到的：

> method 和 benchmark 强耦合。

---

## 十、Benchmark 不应该等于 Dataset

我建议：

```text
Benchmark
=
Dataset
+
Task
+
EnvironmentConfig
+
Protocol
+
Evaluator
```

代码层：

```python
class Benchmark:

    def episodes(self, split):
        ...

    def task_spec(self):
        ...

    def environment_spec(self):
        ...

    def evaluator(self):
        ...

    def capabilities(self):
        ...
```

然后：

```text
benchmarks/

├── aerialvln/
├── traveluav/
├── openfly/
├── citynav/
├── indooruav/
└── embodiednav/
```

每个目录只做适配。

---

## 十一、EpisodeSpec 应该成为 benchmark 数据的公共格式

统一：

```python
@dataclass
class EpisodeSpec:

    episode_id: str
    scene_id: str

    instruction: str

    start_pose: Pose

    goal: GoalSpec

    demonstration: Optional[Trajectory]

    metadata: dict
```

Goal 不一定是 position。

所以：

```text
GoalSpec

├── PointGoal
├── ObjectGoal
├── RegionGoal
├── SemanticGoal
├── RouteGoal
└── TaskGoal
```

例如：

AerialVLN：

```text
RouteGoal
```

CityNav：

```text
Semantic/Location Goal
```

HUGE：

```text
TaskGoal("inspect building")
```

这样才能真正覆盖未来任务。

---

## 十二、TaskSpec

Task 和 benchmark 应该再分开。

```python
class TaskSpec:

    instruction_type

    goal_type

    success_condition

    max_steps

    max_time

    required_capabilities
```

Task taxonomy 可以先定义：

```text
NavigationTask

├── RouteFollowing
├── GoalNavigation
├── ObjectSearch
├── InteractiveNavigation
├── Inspection
├── Landing
├── Exploration
└── MultiAgentNavigation
```

Benchmark 实际只是：

```text
scene + episode + task configuration
```

---

## 十三、Capability Contract

这是你们平台非常可能成为论文贡献的一部分。

每一个 Benchmark 都声明：

```yaml
benchmark: aerialvln

observations:
  rgb:
    required: true
    cameras:
      - front

  depth:
    available: true

  pose:
    available: true
    policy_visible: false

actions:
  supported:
    - discrete_4dof

task:
  type: route_following

environment:
  interactive: true
```

Agent：

```yaml
agent: navid

requires:
  rgb:
    views:
      - front

  instruction: true

  history: true

optional:
  depth: false
  pose: false

outputs:
  type: parameterized_action
```

平台启动：

```text
AgentSpec
   ×
BenchmarkSpec
   ×
EnvironmentCapabilities
       ↓
CompatibilityResolver
```

返回：

```text
NATIVE
ADAPTABLE
INCOMPATIBLE
```

比如：

```text
NaVid × AerialVLN
→ adaptable

TravelUAV × AerialVLN
→ incompatible
reason:
requires 5-view RGB + state
```

这比运行半小时才报 Python error 好得多。

---

## 十四、Agent 层

所有方法统一：

```python
class UAVAgent:

    def reset(self, task_context):
        ...

    def act(
        self,
        observation: Observation
    ) -> AgentAction:
        ...

    def load_checkpoint(self, path):
        ...
```

不要让 Agent 知道：

```text
AirSim
OpenFly
AerialVLN
```

理想情况下 Agent 只知道：

```text
ObservationSpec
ActionSpec
```

目录：

```text
agents/

├── seq2seq/
├── cma/
├── lag/
├── navid/
├── traveluav/
├── openfly_agent/
├── citynav_agent/
├── pi0/
└── see_point_fly/
```

---

## 十五、Model 和 Training Strategy 必须分开

例如 LAG 不应该实现成：

```text
LAGAgent
```

而是：

```text
CMAAgent
+
LookAheadGuidance
```

训练系统：

```text
Trainer

├── OfflineILTrainer
├── TeacherForcingTrainer
├── DAggerTrainer
├── RLTrainer
└── VLATrainer
```

再单独：

```text
SupervisionStrategy

├── GroundTruthAction
├── ShortestPath
├── LookAheadGuidance
└── WaypointSupervision
```

于是可以组合：

```text
Seq2Seq + TeacherForcing
Seq2Seq + DAgger

CMA + TeacherForcing
CMA + DAgger
CMA + LookAheadGuidance
```

平台抽象会干净很多。

---

## 十六、Evaluation 建议做双协议

这一点我非常建议从第一天就确定。

### Native Track

完全遵守原 benchmark。

例如 AerialVLN：

```text
original action
original sensor
original success threshold
original evaluator
```

得到的数字：

> 可以直接和论文比较。

### Unified Track

由你们统一规定，例如：

```text
front RGB
no GT pose
no semantic map
4-DoF waypoint
same max steps
same safety metric
```

然后：

```text
AerialVLN
CityNav
OpenFly
IndoorUAV
```

都尝试用相同 protocol。

回答：

> 模型跨 benchmark 的泛化能力如何？

这应该会成为整个平台最有科研意义的功能之一。

---

## 十七、Metrics 也拆成两部分

```text
NativeMetrics
+
CommonDiagnostics
```

Native：

```text
benchmark 官方 SR / SPL / nDTW...
```

Common diagnostics：

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

这样不能直接比较的 benchmark，也可以得到统一诊断。

---

## 十八、OpenFly 在这个框架里应该怎么放

你的 OpenFly 可以自然变成：

```text
OpenFlyBenchmark
       │
       ├── UE scene
       │
       │   Dynamics = AirSim / Kinematic
       │   Renderer = Unreal
       │   Geometry = Unreal
       │
       ├── AirSim scene
       │
       │   Dynamics = AirSim
       │   Renderer = Unreal
       │   Geometry = Unreal
       │
       ├── 3DGS scene
       │
       │   Dynamics = Kinematic / AirSim
       │   Renderer = SIBR / GS
       │   Geometry = Mesh
       │
       └── GTA scene
           Dynamics = GTA / Kinematic
           Renderer = GTA
           Geometry = GTA / proxy
```

但对于 Agent 来说：

```python
env.reset()

obs = env.observe()

action = agent.act(obs)

obs, reward, terminated, info = env.step(action)
```

完全一样。

这才是真正的大一统。

---

## 十九、推荐代码目录

我会按下面这个结构开始。

```text
uavvln/

├── core/
│   ├── pose.py
│   ├── state.py
│   ├── observation.py
│   ├── action.py
│   ├── episode.py
│   ├── task.py
│   ├── capability.py
│   └── coordinate.py
│
├── env/
│   │
│   ├── environment.py
│   │
│   ├── dynamics/
│   │   ├── base.py
│   │   ├── kinematic.py
│   │   ├── airsim.py
│   │   └── project_airsim.py
│   │
│   ├── renderer/
│   │   ├── base.py
│   │   ├── unreal.py
│   │   ├── gaussian.py
│   │   ├── gtav.py
│   │   └── replay.py
│   │
│   ├── geometry/
│   │   ├── base.py
│   │   ├── mesh.py
│   │   ├── unreal.py
│   │   └── occupancy.py
│   │
│   └── sensors/
│       ├── camera.py
│       ├── depth.py
│       ├── imu.py
│       └── gps.py
│
├── controller/
│   ├── discrete.py
│   ├── waypoint.py
│   ├── velocity.py
│   └── trajectory.py
│
├── benchmarks/
│   ├── aerialvln/
│   ├── openfly/
│   ├── traveluav/
│   ├── citynav/
│   └── indooruav/
│
├── agents/
│   ├── seq2seq/
│   ├── cma/
│   ├── navid/
│   ├── traveluav/
│   └── openfly_agent/
│
├── trainers/
│   ├── imitation.py
│   ├── dagger.py
│   ├── rl.py
│   └── vla.py
│
├── evaluation/
│   ├── evaluator.py
│   ├── native.py
│   ├── unified.py
│   └── metrics.py
│
├── registry/
│   ├── benchmark_registry.py
│   ├── agent_registry.py
│   └── backend_registry.py
│
├── runtime/
│   ├── runner.py
│   ├── rollout.py
│   └── distributed.py
│
├── configs/
│
├── tools/
│
└── tests/
```

这套目录结构基本可以长期维持。

---

## 二十、用户真正运行平台时应该非常简单

例如：

```bash
uavvln eval \
    benchmark=aerialvln \
    agent=cma \
    split=val_unseen
```

或者：

```bash
uavvln eval \
    benchmark=openfly \
    scene_backend=gaussian \
    agent=navid
```

训练：

```bash
uavvln train \
    benchmark=aerialvln \
    agent=cma \
    trainer=dagger
```

或者 Python：

```python
benchmark = make_benchmark("aerialvln")

agent = make_agent("cma")

runner = Runner(
    benchmark=benchmark,
    agent=agent,
)

runner.evaluate()
```

用户不应该写任何：

```python
airsim.MultirotorClient()
```

或者：

```python
SIBR_gaussianViewer_app
```

这些都应该隐藏在 backend。

---

## 二十一、配置建议采用组合式配置

例如：

```yaml
experiment:
  name: cma_aerialvln

benchmark:
  name: aerialvln
  split: val_unseen

agent:
  name: cma
  checkpoint: checkpoints/cma.pt

environment:
  dynamics:
    backend: airsim

  renderer:
    backend: unreal

  geometry:
    backend: unreal

evaluation:
  protocol: native
```

3DGS：

```yaml
environment:

  dynamics:
    backend: kinematic

  renderer:
    backend: gaussian
    scene: env_gs_001

  geometry:
    backend: mesh
    scene: env_gs_001_mesh
```

这样你以后切环境，不动 Agent。

---

## 二十二、我建议按照 6 个阶段开发

| 阶段 | 内容 | 目标 |
|---|---|---|
| Phase 0 | Core Spec + Kinematic Backend | 无 simulator 也能跑完整 episode |
| Phase 1 | AirSim + AerialVLN + Seq2Seq/CMA | 打通第一条完整 pipeline |
| Phase 2 | OpenFly UE/AirSim | 验证一个 benchmark 多环境 |
| Phase 3 | 3DGS Renderer + Mesh Geometry | 验证 renderer/dynamics 解耦 |
| Phase 4 | TravelUAV + continuous trajectory | 验证连续动作与 trajectory |
| Phase 5 | Native/Unified Evaluation | 开始真正 cross-benchmark experiment |
| Phase 6 | GTA / Habitat / PX4 / VLA | 扩展生态 |

其中 Phase 0 非常重要。

先写：

```text
KinematicBackend
+
DummyRenderer
+
ToyBenchmark
+
RandomAgent
```

验证：

```text
reset
observe
act
step
evaluate
```

整个 protocol 正确。

否则一上来就调 AirSim，系统设计问题和 simulator bug 会混在一起。

---

## 二十三、第一版我建议只支持三个 Benchmark

不要一开始做十个。

第一版：

```text
AerialVLN
OpenFly
TravelUAV
```

原因非常好。

AerialVLN：

```text
discrete
classic VLN
AirSim
Seq2Seq/CMA
```

OpenFly：

```text
multiple renderer
modern VLM/VLA
long history
```

TravelUAV：

```text
multi-view
continuous
6DoF trajectory
MLLM
```

这三个已经足够把整个 architecture 压测一遍。

如果它们能共存：

```text
benchmark abstraction
observation abstraction
action abstraction
controller abstraction
environment abstraction
```

基本说明设计方向是对的。

---

## 二十四、方法第一版也只做 5–6 个

我建议：

```text
Seq2Seq
CMA
LAG
NaVid
TravelUAV
OpenFly-Agent
```

这六个刚好覆盖：

```text
RNN
cross-modal attention
training strategy
video VLM
hierarchical trajectory
VLA
```

同样不建议一上来把所有 SOTA 都搬进去。

---

## 二十五、有几条架构纪律建议从第一天强制执行

最重要的是下面这些。

```text
Agent 代码里禁止出现：
    AirSim
    AerialVLN
    OpenFly

Benchmark 代码里禁止直接调用：
    AirSim API
    SIBR API

Evaluator 禁止给 Agent privileged information

所有坐标转换：
    只能存在于 CoordinateAdapter

所有 simulator native action：
    只能存在于 DynamicsBackend / ControllerAdapter

所有场景差异：
    只能存在于 Backend / Benchmark plugin
```

如果后面出现：

```python
if benchmark == "openfly":
    ...
elif benchmark == "aerialvln":
    ...
```

而且这种判断开始进入 Agent/Trainer/Core 中：

> 基本说明抽象层有问题。

---

## 二十六、从研究角度，你们的平台真正核心不是代码

最终论文贡献最好不是：

> “We integrate 8 UAV-VLN benchmarks.”

更有价值的表述是：

```text
1. UAV Navigation Task Specification

2. Composable Environment Architecture
   Dynamics × Rendering × Geometry

3. Capability-aware Agent–Benchmark Interface

4. Native + Unified Cross-Benchmark Evaluation

5. Cross-Benchmark Generalization Study
```

其中尤其是：

```text
Dynamics / Rendering / Geometry 解耦
```

和：

```text
Agent × Benchmark Capability Contract
```

可能成为你们区别于普通 benchmark collection 的核心。

最终可以把整个项目概括成一个公式：

\[
\boxed{
Experiment =
Agent
\times
Task
\times
Benchmark
\times
Dynamics
\times
Renderer
\times
Geometry
\times
Protocol
}
\]

而不是目前 UAV-VLN 经常采用的：

\[
\text{Method}=\text{Model}+\text{Benchmark}+\text{Simulator}
\]

你们真正想做的，就是把后者拆开。

---

## 实施建议

如果接下来准备正式开始写代码，我建议第一步只实现：

```text
core/
KinematicBackend
ToyBenchmark
RandomAgent
Runner
```

先把这五个模块的接口定死，再开始接 AirSim。

这样整个项目后面会少很多重构。
