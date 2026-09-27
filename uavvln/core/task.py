from dataclasses import dataclass, field

@dataclass(frozen=True)
class TaskSpec:
    name: str = "navigation"
    instruction_type: str = "text"
    goal_type: str = "point"
    max_steps: int = 100
    max_time: float | None = None
    required_capabilities: tuple[str, ...] = ()
    def __post_init__(self):
        if self.max_steps <= 0: raise ValueError("max_steps must be positive")

@dataclass(frozen=True)
class NavigationTask(TaskSpec):
    name: str = "goal_navigation"
