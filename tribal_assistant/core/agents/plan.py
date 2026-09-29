"""Plan progress (no model needed) and a rule-based planner used when AI is off or fails."""

from tribal_assistant.core.agents.context import VillageContext
from tribal_assistant.core.agents.knobs import tuning
from tribal_assistant.core.agents.knowledge import GameKnowledge
from tribal_assistant.core.agents.pacing import BuildPacing
from tribal_assistant.core.agents.protection import Protection
from tribal_assistant.core.agents.quests import QuestRules
from tribal_assistant.core.schemas.plan import PlanStep


class PlanTracker:
    """Marks each step pending, queued, done or blocked from the synced village state."""

    def evaluate(self, ctx: VillageContext, steps: list[PlanStep]) -> list[PlanStep]:
        return [self._evaluate(ctx, step) for step in steps]

    def _evaluate(self, ctx: VillageContext, step: PlanStep) -> PlanStep:
        step = step.model_copy()

        if step.kind == "build":
            building = ctx.building(step.target)
            if building is None:
                step.status, step.note = "blocked", "edifício inexistente"
            elif building.level >= step.amount:
                step.status, step.note = "done", f"nível {building.level}"
            elif building.queued_level and building.queued_level >= step.amount:
                step.status, step.note = "queued", f"na fila → {building.queued_level}"
            else:
                missing = GameKnowledge.missing_requirements(step.target, ctx.levels)
                step.status = "blocked" if missing else "pending"
                step.note = (
                    "requer " + ", ".join(f"{k} {v}" for k, v in missing.items())
                    if missing
                    else f"nível {building.level}/{step.amount}"
                )

        elif step.kind == "recruit":
            unit = ctx.unit(step.target)
            total = unit.total if unit else 0
            queued = sum(r.count for r in ctx.village.recruit_orders if r.unit == step.target)
            if total >= step.amount:
                step.status, step.note = "done", f"{total} tropas"
            elif total + queued >= step.amount:
                step.status, step.note = "queued", f"{total} + {queued} recrutando"
            elif unit is None or not unit.available:
                step.status, step.note = "blocked", (unit.blocker if unit else None) or "indisponível"
            else:
                step.status, step.note = "pending", f"{total}/{step.amount}"

        elif step.kind == "unlock_scavenge":
            option = next((o for o in ctx.village.scavenge if str(o.option_id) == step.target), None)
            if option is None:
                step.status, step.note = "blocked", "coleta desconhecida"
            elif not option.is_locked:
                step.status, step.note = "done", "desbloqueada"
            elif option.unlock_at is not None:
                step.status, step.note = "queued", "desbloqueando"
            else:
                step.status, step.note = "pending", "bloqueada"

        return step

    @staticmethod
    def next_builds(steps: list[PlanStep]) -> list[str]:
        return [s.target for s in steps if s.kind == "build" and s.status == "pending"]

    @staticmethod
    def next_recruits(steps: list[PlanStep]) -> list[PlanStep]:
        return [s for s in steps if s.kind == "recruit" and s.status == "pending"]

    @staticmethod
    def next_unlocks(steps: list[PlanStep]) -> list[int]:
        return [int(s.target) for s in steps if s.kind == "unlock_scavenge" and s.status == "pending"]

    @staticmethod
    def needs_refresh(steps: list[PlanStep]) -> bool:
        if not steps:
            return True

        open_steps = [s for s in steps if s.status in ("pending", "queued")]
        return not open_steps or all(s.status == "blocked" for s in steps if s.status != "done")


class RulePlanner:
    """Early game after the forum sprint: statue early, quests, main building, wood-led pits, gate to light cavalry."""

    STABLE_PATH = (("main", 10), ("barracks", 5), ("smith", 5), ("stable", 3))
    STORAGE_FOR_STABLE = 6

    def plan(self, ctx: VillageContext) -> tuple[str, list[PlanStep]]:
        knobs = tuning(ctx)
        levels = ctx.levels
        village = ctx.village
        steps: list[PlanStep] = []
        seen: set[tuple[str, str]] = set()

        def add(kind: str, target: str, amount: int, reason: str) -> None:
            key = (kind, target)
            if key in seen:
                return

            seen.add(key)
            steps.append(PlanStep(kind=kind, target=target, amount=amount, reason=reason))

        if levels.get("barracks", 0) >= 1 and ctx.building("statue") is not None and levels.get("statue", 0) < 1:
            add("build", "statue", 1, "estátua cedo: paladino saqueia desde o início")

        for building, level, title in QuestRules.building_goals(ctx.quests, levels, knobs):
            add("build", building, level, f"missão: {title}")

        if levels.get("main", 0) < BuildPacing.main_cap(levels, knobs):
            add("build", "main", levels.get("main", 0) + 1, "edifício principal sem parar: acelera todas as obras")

        biggest = max(ctx.stock.get(r, 0) for r in ("wood", "clay", "iron"))
        hourly = max(village.wood_prod, village.clay_prod, village.iron_prod, 1)
        if village.storage and (biggest / village.storage > knobs.get("plan.storage_fill_share") or village.storage / hourly < knobs.get("plan.storage_min_hours")):
            add("build", "storage", levels.get("storage", 0) + 1, "armazém antes de encher: recurso perdido atrasa tudo")

        if village.pop_max and ctx.pop_free < max(knobs.int("plan.farm_min_free"), village.pop_max * knobs.get("farm.free_share")):
            add("build", "farm", levels.get("farm", 0) + 1, "fazenda antes de a população travar")

        for pit in BuildPacing.pits(levels, knobs):
            if levels.get(pit, 0) < 30:
                add("build", pit, levels.get(pit, 0) + 1, "madeira na frente, ferro 3 abaixo até o estábulo")

        self._stable_gate(ctx, add)

        for building in BuildPacing.military_due(levels, Protection.active(ctx), knobs):
            add("build", building, levels.get(building, 0) + 1, "fora da proteção: 2 de quartel e estábulo a cada 3 de EP")

        wall = knobs.int("defense.wall_target")
        if Protection.ending(ctx) and levels.get("wall", 0) < wall:
            add("build", "wall", levels.get("wall", 0) + 1, f"fim da proteção: muralha {wall}")

        locked = sorted(o.option_id for o in village.scavenge if o.is_locked and o.unlock_at is None)
        if locked:
            add("unlock_scavenge", str(locked[0]), 1, "coleta rende recursos sem arriscar tropas")

        light = ctx.unit("light")
        if light and light.available:
            add("recruit", "light", max(knobs.int("plan.light_min"), light.total + knobs.int("plan.light_step")), "cavalaria leve é a melhor unidade de saque")
        else:
            spear = ctx.unit("spear")
            if spear and spear.available and spear.total < 40:
                add("recruit", "spear", min(40, spear.total + 10), "lanceiros para saque, coleta e a missão dos 40")

        if any(c["direction"] == "in" and c["kind"] in ("attack", "noble") for c in ctx.commands):
            add("build", "wall", levels.get("wall", 0) + 1, "ataque chegando: muralha")

        summary = (
            f"Plano automático: {sum(1 for s in steps if s.kind == 'build')} obras — estátua cedo, missões, "
            "edifício principal até 10, madeira na frente e ferro abaixo, portão da cavalaria leve."
        )
        return summary, steps[:12]

    def _stable_gate(self, ctx: VillageContext, add) -> None:
        """EP 10, Quartel 5, Ferreiro 5, Estábulo 3, with the storage holding the next cost."""
        levels = ctx.levels
        for building, target in self.STABLE_PATH:
            if levels.get(building, 0) >= target:
                continue

            nxt = ctx.building(building)
            cost = max((nxt.next_wood or 0, nxt.next_clay or 0, nxt.next_iron or 0)) if nxt else 0
            storage = ctx.village.storage or 0
            wants_storage = levels.get("main", 0) >= 10 and levels.get("storage", 0) < self.STORAGE_FOR_STABLE
            if storage and (cost > storage * 0.95 or wants_storage):
                add("build", "storage", levels.get("storage", 0) + 1, "armazém 6-7 comporta o caminho do estábulo")

            add("build", building, levels.get(building, 0) + 1, "portão da cavalaria leve: EP 10, Quartel 5, Ferreiro 5, Estábulo 3")
            return
