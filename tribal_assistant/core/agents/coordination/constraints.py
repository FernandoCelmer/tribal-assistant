"""Hard rules above the score: temporary vetoes declared by a proposer, with reason and expiry."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from tribal_assistant.core.agents.coordination.proposal import Proposal

TROOP_ACTIONS = ("send_farm_attack", "send_farm_template", "send_scavenge", "send_spy", "send_noble")


@dataclass
class Constraint:
    kind: str
    reason: str
    source: str
    until: datetime | None = None
    blocks: tuple[str, ...] = ()
    min_confidence: float = 0.0

    def violated_by(self, proposal: Proposal) -> bool:
        if self.kind == "hold_troops":
            return proposal.action in TROOP_ACTIONS

        if self.kind == "block_actions":
            return proposal.action in self.blocks

        if self.kind == "min_confidence":
            return proposal.action in self.blocks and proposal.confidence < self.min_confidence

        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "reason": self.reason,
            "source": self.source,
            "until": self.until.isoformat() if self.until else None,
            "blocks": list(self.blocks),
            "min_confidence": self.min_confidence,
        }
