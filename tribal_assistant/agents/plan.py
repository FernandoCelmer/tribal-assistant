"""Plan progress (no model needed) and a rule-based planner used when AI is off or fails."""

from tribal_assistant.agents.context import VillageContext
from tribal_assistant.agents.knowledge import GameKnowledge
from tribal_assistant.schemas.plan import PlanStep

RESOURCES = ("wood", "stone", "iron")


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
    """Early-game plan: main building nonstop, balanced pits, storage and farm ahead of the caps, path to the stable."""

    STABLE_PATH = (("main", 10), ("barracks", 5), ("smith", 5), ("stable", 3))

    def plan(self, ctx: VillageContext) -> tuple[str, list[PlanStep]]:
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

        for quest in ctx.quests:
            for goal in quest.get("goals", []):
                mapped = GameKnowledge.goal_building(f"{goal.get('title', '')} {goal.get('text', '')}")
                if mapped and mapped[0] not in ("wall", "hide") and levels.get(mapped[0], 0) < mapped[1]:
                    add("build", mapped[0], mapped[1], f"missão: {quest.get('title', '')}")

        if levels.get("main", 0) < 20:
            add("build", "main", levels.get("main", 0) + 1, "edifício principal sem parar: acelera todas as obras")

        biggest = max(ctx.stock.get(r, 0) for r in ("wood", "clay", "iron"))
        hourly = max(village.wood_prod, village.clay_prod, village.iron_prod, 1)
        if village.storage and (biggest / village.storage > 0.6 or village.storage / hourly < 6):
            add("build", "storage", levels.get("storage", 0) + 1, "armazém antes de encher: recurso perdido atrasa tudo")

        if village.pop_max and ctx.pop_free < max(20, village.pop_max * 0.15):
            add("build", "farm", levels.get("farm", 0) + 1, "fazenda antes de a população travar")

        pits = sorted(RESOURCES, key=lambda b: levels.get(b, 0))
        for pit in pits:
            if levels.get(pit, 0) < 30:
                add("build", pit, levels.get(pit, 0) + 1, "minas equilibradas: produção por hora primeiro")

        for building, target in self.STABLE_PATH:
            if levels.get(building, 0) < target:
                add("build", building, levels.get(building, 0) + 1, "caminho do estábulo: cavalaria leve para saquear")
                break

        locked = sorted(o.option_id for o in village.scavenge if o.is_locked and o.unlock_at is None)
        if locked:
            add("unlock_scavenge", str(locked[0]), 1, "coleta rende recursos sem arriscar tropas")

        light = ctx.unit("light")
        if light and light.available:
            add("recruit", "light", max(10, light.total + 5), "cavalaria leve é a melhor unidade de saque")
        else:
            spear = ctx.unit("spear")
            if spear and spear.available and spear.total < 30:
                add("recruit", "spear", min(30, spear.total + 10), "tropas para saque, coleta e missões")

        if any(c["direction"] == "in" and c["kind"] in ("attack", "noble") for c in ctx.commands):
            add("build", "wall", levels.get("wall", 0) + 1, "ataque chegando: muralha")

        summary = (
            f"Plano automático: {sum(1 for s in steps if s.kind == 'build')} obras — edifício principal contínuo, "
            "minas equilibradas, armazém e fazenda à frente dos limites, caminho do estábulo."
        )
        return summary, steps[:12]
