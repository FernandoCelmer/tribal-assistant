"""Plan progress (no model needed) and a rule-based planner used when AI is off or fails."""

from tribal_assistant.agents.context import VillageContext
from tribal_assistant.agents.knowledge import GameKnowledge
from tribal_assistant.schemas.plan import PlanStep

RESOURCES = ("wood", "stone", "iron")
NOBLE_PATH = (("main", 20), ("smith", 20), ("market", 10), ("snob", 1))


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
    """A sensible default plan from quests, the advisor, economy balance and the noble path."""

    def plan(self, ctx: VillageContext) -> tuple[str, list[PlanStep]]:
        levels = ctx.levels
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
                if mapped and levels.get(mapped[0], 0) < mapped[1]:
                    add("build", mapped[0], mapped[1], f"missão: {quest.get('title', '')}")

        for rec in ctx.village.recommendations:
            if rec.priority == "high":
                add("build", rec.building, rec.to_level, rec.reason)

        lowest = min(RESOURCES, key=lambda b: levels.get(b, 0))
        add("build", lowest, levels.get(lowest, 0) + 1, "equilibrar produção")

        target_pits = min(30, levels.get("main", 1) + 3)
        for pit in RESOURCES:
            if levels.get(pit, 0) < target_pits:
                add("build", pit, min(levels.get(pit, 0) + 2, target_pits), "produção acompanha o edifício principal")

        if levels.get("barracks", 0) < 3:
            add("build", "barracks", 3, "recrutar e liberar missões de exército")

        if levels.get("smith", 0) < 1 and levels.get("main", 0) >= 5:
            add("build", "smith", 1, "libera pesquisas e o caminho do nobre")

        if levels.get("market", 0) < 1 and levels.get("main", 0) >= 3 and levels.get("storage", 0) >= 2:
            add("build", "market", 1, "mercado para trocas futuras")

        building, target = min(NOBLE_PATH, key=lambda nt: levels.get(nt[0], 0) / nt[1])
        if levels.get(building, 0) < target:
            add("build", building, levels.get(building, 0) + 1, "caminho do primeiro nobre")

        locked = sorted(o.option_id for o in ctx.village.scavenge if o.is_locked)
        if locked:
            add("unlock_scavenge", str(locked[0]), 1, "coleta rende recursos sem arriscar tropas")

        spear = ctx.unit("spear")
        if spear and spear.available:
            add("recruit", "spear", max(20, spear.total + 10), "tropas de saque e defesa")

        light = ctx.unit("light")
        if light and light.available:
            add("recruit", "light", max(10, light.total + 5), "cavalaria leve é a melhor unidade de saque")

        summary = (
            f"Plano automático: {sum(1 for s in steps if s.kind == 'build')} obras, "
            f"prioridade em missões, armazém/fazenda e caminho do nobre ({building} {target})."
        )
        return summary, steps[:12]
