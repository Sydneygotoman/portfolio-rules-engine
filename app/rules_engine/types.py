from dataclasses import dataclass
from typing import Literal

Status = Literal["pass", "breach", "warning"]


@dataclass
class RuleResult:
    rule_name: str
    status: Status
    computed_value: float
    threshold: float
    reason: str
    asset: str | None = None
