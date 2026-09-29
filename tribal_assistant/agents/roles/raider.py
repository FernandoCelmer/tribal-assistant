"""Rally point: loot nearby barbarian villages with the troops at home."""

import json
from typing import TYPE_CHECKING

from tribal_assistant.agents.roles.base import VillageAgent

if TYPE_CHECKING:
    from tribal_assistant.agents.toolbox import Toolbox

SQUADS = ({"light": 5}, {"spear": 10}, {"axe": 10}, {"spear": 5})
MAX_PER_ROUND = 3
SCAVENGERS = ("spear", "sword", "axe", "archer", "light", "marcher", "heavy")


class RaiderAgent(VillageAgent):
    key = "raider"
    title = "Saqueador"
    mission = (
        "Saquear aldeias bárbaras próximas com as tropas em casa: escolha os alvos mais perto que não "
        "foram atacados recentemente e mande grupos pequenos (5 cavalaria leve ou 10 lanceiros). "
        "Nunca ataque jogadores. Mantenha tropas em casa se houver ataque chegando. "
        "Tropas que sobrarem depois dos saques vão coletar no nível de coleta mais alto que estiver livre."
    )
    tools = ("get_village_state", "list_barbarians", "send_farm_attack", "send_scavenge", "lookup_knowledge")

    def needs_llm(self, ctx, config) -> bool:
        return False

    async def rules(self, box: "Toolbox") -> str:
        ctx = box.ctx

        if any(c["direction"] == "in" and c["kind"] in ("attack", "noble") for c in ctx.commands):
            return "ataque chegando; tropas ficam em casa"

        notes = [await self._farm(box)]
        notes.append(await self._scavenge(box))

        return "; ".join(n for n in notes if n)

    async def _farm(self, box: "Toolbox") -> str:
        ctx = box.ctx

        listing = await box.invoke("list_barbarians", {})
        if not listing.ok or not listing.text.startswith("["):
            return listing.text

        targets = [t for t in json.loads(listing.text) if not t.get("recently_attacked")]
        sent = []

        for target in targets:
            if len(sent) >= MAX_PER_ROUND:
                break

            squad = next(
                (s for s in SQUADS if all((ctx.unit(u) and ctx.unit(u).home >= n) for u, n in s.items())),
                None,
            )
            if squad is None:
                break

            outcome = await box.invoke(
                "send_farm_attack",
                {"target": target["coords"], "units": squad, "reason": "saque de bárbara próxima"},
            )
            if outcome.ok:
                sent.append(target["coords"])

        return f"saques: {', '.join(sent)}" if sent else "nenhum saque (sem tropas ou alvos)"

    async def _scavenge(self, box: "Toolbox") -> str:
        ctx = box.ctx

        free = sorted(
            (o for o in ctx.village.scavenge if not o.is_locked and o.return_at is None),
            key=lambda o: o.option_id,
            reverse=True,
        )
        if not free:
            return ""

        units = {u: ctx.unit(u).home for u in SCAVENGERS if ctx.unit(u) and ctx.unit(u).home > 0}
        if not units:
            return ""

        outcome = await box.invoke(
            "send_scavenge",
            {"option_id": free[0].option_id, "units": units, "reason": "tropas ociosas coletando recursos"},
        )
        return outcome.text
