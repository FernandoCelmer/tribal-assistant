"""Compact text views of a village, sliced per agent, to keep prompts small."""

from typing import ClassVar

from tribal_assistant.core.agents.clock import Clock
from tribal_assistant.core.agents.context import VillageContext
from tribal_assistant.core.agents.knowledge import GameKnowledge

STATUS = {"pending": "pendente", "queued": "em andamento", "done": "feito", "blocked": "bloqueado"}
KIND = {"build": "construir", "recruit": "recrutar", "unlock_scavenge": "desbloquear coleta"}


class ContextView:
    SECTIONS: ClassVar[dict[str, tuple[str, ...]]] = {
        "strategist": ("resources", "queue", "buildings", "troops", "scavenge", "quests", "plan", "commands", "recent", "beliefs", "sightings", "lessons", "coordination"),
        "quartermaster": ("quests",),
        "operator": ("resources", "queue", "buildings", "troops", "scavenge", "quests", "plan", "commands", "recent", "beliefs", "sightings", "lessons", "coordination"),
    }

    def __init__(self, ctx: VillageContext, queue_slots: int) -> None:
        self.ctx = ctx
        self.queue_slots = queue_slots
        self.clock = Clock()

    def render(self, role: str = "operator") -> str:
        v = self.ctx.village
        player = self.ctx.player or {}
        lines = [
            f"Aldeia {v.name} ({v.coords}) · {v.points} pontos",
            self.clock.header(v.synced_at, player.get("protection_until")),
        ]

        lines += [text for text in (self.ctx.absence, self.ctx.absence_soon) if text]

        for section in self.SECTIONS.get(role, self.SECTIONS["operator"]):
            text = getattr(self, section)()
            if text:
                lines.append(text)

        if self.ctx.goal:
            written = self.clock.relative(self.ctx.goal_set_at)
            lines.append(f"Objetivo{' definido ' + written if written else ''}: {self.ctx.goal}")

        return "\n".join(lines)

    def resources(self) -> str:
        v = self.ctx.village
        s = self.ctx.stock
        return (
            f"Recursos: madeira {s['wood']}, argila {s['clay']}, ferro {s['iron']} (armazém {v.storage}) · "
            f"produção/h +{v.wood_prod}/+{v.clay_prod}/+{v.iron_prod} · "
            f"população {v.pop_current}/{v.pop_max} ({self.ctx.pop_free} livre)"
        )

    def queue(self) -> str:
        queued = self.ctx.queue
        free = max(0, self.queue_slots - len(queued))
        items = ", ".join(self._queued(q) for q in queued) or "vazia"
        return f"Fila de obras: {items} ({free} vaga(s) livre(s))"

    def _queued(self, q: dict) -> str:
        until = self.clock.when(q.get("until"))
        return f"{q['building']}→{q['level']}" + (f" termina {until}" if until else "")

    def _building_line(self, b) -> str:
        if b.max_level and b.level >= b.max_level:
            return f"{b.name} {b.level} (máximo)"

        cost = f"{b.next_wood}/{b.next_clay}/{b.next_iron} pop {b.next_pop}"
        missing = GameKnowledge.missing_requirements(b.name, self.ctx.levels)
        if missing:
            state = "requer " + ", ".join(f"{k} {lvl}" for k, lvl in missing.items())
        elif b.queued_level:
            state = f"na fila→{b.queued_level}"
        elif b.can_build:
            state = "pode"
        else:
            state = self.clock.annotate(b.blocker) if b.blocker else "sem recursos"

        return f"{b.name} {b.level}→{b.next_level} [{cost}] {state}"

    def _buildings(self, names: tuple[str, ...] | None) -> str:
        rows = [self._building_line(b) for b in self.ctx.village.buildings if names is None or b.name in names]
        return "Edifícios: " + " · ".join(rows) if rows else ""

    def buildings(self) -> str:
        return self._buildings(None)

    def troops(self) -> str:
        units = self.ctx.village.units
        home = ", ".join(f"{u.name} {u.home}" for u in units if u.home) or "nenhuma"
        away = ", ".join(f"{u.name} {u.away}" for u in units if u.away) or "nenhuma"
        recruit = ", ".join(f"{u.name}(máx {u.max_recruit})" for u in units if u.available) or "nada"
        queue = ", ".join(
            f"{r.count} {r.unit}" + (f" até {self.clock.when(r.finishes_at)}" if r.finishes_at else "")
            for r in self.ctx.village.recruit_orders
        ) or "nada"
        return f"Tropas em casa: {home} · fora: {away} · recrutável: {recruit} · recrutando: {queue}"

    def scavenge(self) -> str:
        options = self.ctx.village.scavenge
        if not options:
            return ""

        def state(o) -> str:
            if o.is_locked:
                return f"desbloqueando, pronta {self.clock.when(o.unlock_at)}" if o.unlock_at else "bloqueada"
            return f"em andamento, volta {self.clock.when(o.return_at)}" if o.return_at else "livre"

        return "Coleta: " + ", ".join(f"{o.option_id} {state(o)}" for o in options)

    def quests(self) -> str:
        parts = []
        for q in self.ctx.quests:
            goals = ", ".join(
                f"{g.get('title', '')} {g.get('current')}/{g.get('target')}" if g.get("target") else g.get("title", "")
                for g in q.get("goals", [])
            )
            ready = " [pronta]" if q.get("can_complete") else ""
            parts.append(f"{q['id']} {q['title']}{ready}: {goals}")

        rewards = f" · recompensas prontas: {self.ctx.rewards_pending}" if self.ctx.rewards_pending else ""
        return ("Missões: " + " | ".join(parts) + rewards) if parts else (rewards.strip(" ·") or "")

    def plan(self) -> str:
        if not self.ctx.plan:
            return "Plano: nenhum"

        rows = [
            f"{i}. {KIND.get(s.kind, s.kind)} {s.target} {s.amount} [{STATUS.get(s.status, s.status)}{': ' + s.note if s.note else ''}]"
            for i, s in enumerate(self.ctx.plan, 1)
        ]
        written = self.clock.relative(self.ctx.plan_refreshed_at)
        return f"Plano{' escrito ' + written if written else ''}:\n" + "\n".join(rows)

    def commands(self) -> str:
        incoming = [c for c in self.ctx.commands if c["direction"] == "in" and c["kind"] in ("attack", "noble")]
        outgoing = [c for c in self.ctx.commands if c["direction"] == "out"]
        if not incoming and not outgoing:
            return ""
        alert = "nenhum ataque chegando"
        if incoming:
            first = min(c["arrival_at"] for c in incoming)
            alert = f"ATAQUES CHEGANDO: {len(incoming)}, o primeiro {self.clock.when(first)}"

        moving = f"{len(outgoing)} saindo"
        if outgoing:
            moving += f", o próximo chega {self.clock.when(min(c['arrival_at'] for c in outgoing))}"
        return f"Comandos: {alert} · {moving}"

    def recent(self) -> str:
        rows = [
            f"- {self.clock.relative(d['at'])}: {d['agent']} {d['action']} "
            f"{'ok' if d['ok'] else 'falhou'} — {d['result'][:90]}"
            for d in self.ctx.recent
            if d["action"] != "summary"
        ][:6]
        return "Feito há pouco:\n" + "\n".join(rows) if rows else ""

    def beliefs(self) -> str:
        return self.ctx.beliefs

    def sightings(self) -> str:
        return self.ctx.sightings

    def lessons(self) -> str:
        return self.ctx.lessons

    def coordination(self) -> str:
        return self.ctx.coordination
