"""What a game action reports back."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActionResult:
    ok: bool
    action: str
    detail: str
    data: dict[str, Any] = field(default_factory=dict)
