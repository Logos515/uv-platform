from dataclasses import dataclass, field
from enum import Enum

class Compatibility(str, Enum):
    NATIVE = "native"
    ADAPTABLE = "adaptable"
    INCOMPATIBLE = "incompatible"

@dataclass(frozen=True)
class CapabilitySpec:
    observations: frozenset[str] = frozenset({"instruction", "rgb"})
    actions: frozenset[str] = frozenset({"discrete"})
    flags: frozenset[str] = frozenset()
    def supports(self, required):
        return set(required).issubset(self.observations | self.actions | self.flags)

@dataclass(frozen=True)
class CompatibilityResult:
    status: Compatibility
    reasons: tuple[str, ...] = ()

def resolve_compatibility(agent: CapabilitySpec, environment: CapabilitySpec):
    missing = sorted(agent.observations - environment.observations)
    if missing:
        return CompatibilityResult(Compatibility.INCOMPATIBLE, tuple(f"missing observation: {x}" for x in missing))
    if agent.actions.issubset(environment.actions):
        return CompatibilityResult(Compatibility.NATIVE)
    return CompatibilityResult(Compatibility.ADAPTABLE, ("action conversion required",))
