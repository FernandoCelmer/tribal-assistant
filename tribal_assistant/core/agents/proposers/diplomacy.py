"""Diplomacy: tribe, mentor and the social side of the game, never with the other accounts run here."""

from tribal_assistant.core.agents.coordination.proposal import Factors, Horizon, Proposal
from tribal_assistant.core.agents.coordination.view import CoordinationView
from tribal_assistant.core.agents.proposers.base import Proposer
from tribal_assistant.core.agents.proposers.economy import EconomyProposer

APPLY_RETRY_HOURS = 48


class DiplomacyProposer(Proposer):
    key = "diplomacy"
    title = "Diplomacia"
    observes = "convites e tribos da região, ofertas de mentor"
    delivers = "entrada numa tribo forte e um mentor, sem tratar com as outras contas daqui"

    async def propose(self, view: CoordinationView) -> list[Proposal]:
        if view.dry_run:
            return []

        items: list[Proposal] = []
        for step in (self._tribe, self._mentor):
            try:
                items += await step(view)
            except Exception as exc:
                view.note_error = str(exc)

        return items

    def _social(self, action: str, arguments: dict[str, str], reason: str, benefit: str, impact: float) -> Proposal:
        return Proposal(
            self.key,
            action,
            {**arguments, "reason": reason[:60]},
            reason,
            benefit,
            factors=Factors(urgency=0.3, impact=impact, opportunity=0.6),
            horizon=Horizon.STRATEGIC,
            confidence=0.8,
        )

    async def _tribe(self, view: CoordinationView) -> list[Proposal]:
        from tribal_assistant.core.game.diplomacy import Diplomacy

        if (view.ctx.player or {}).get("ally_id") or not await view.cooldown("tribe", 12):
            return []

        state = await view.actions.diplomacy.tribes(view.ctx.game_id)
        if state.get("in_tribe"):
            return []

        if state.get("invites"):
            invite = state["invites"][0]
            return [self._social("accept_tribe_invite", {"invite_id": str(invite["id"])}, f"convite da tribo {invite.get('tag', '')}", "proteção, apoio e comércio da tribo", 0.7)]

        skip = {t["id"] for t in state.get("nearby", []) if not await view.lessons.due(f"tribe_apply:{t['id']}", APPLY_RETRY_HOURS)}
        best = Diplomacy.best_tribe(state.get("nearby", []), skip)
        if best is None:
            return []

        await view.lessons.mark(f"tribe_apply:{best['id']}")
        return [self._social("apply_to_tribe", {"ally_id": str(best["id"])}, f"tribo mais forte da região: {best['tag']}", f"{best['members']} membros, {best['points']} pontos", 0.6)]

    async def _mentor(self, view: CoordinationView) -> list[Proposal]:
        from tribal_assistant.core.game.diplomacy import Diplomacy

        if not await view.cooldown("mentor", 24):
            return []

        mentors = await view.actions.diplomacy.mentors(view.ctx.game_id)
        best = Diplomacy.best_mentor(mentors, await EconomyProposer.managed_players(view))
        if best is None:
            return []

        return [self._social("accept_mentor", {"mentor_id": str(best["id"])}, f"mentor recomendado: {best['name']}", "ajuda de jogador experiente e a conquista Graduado", 0.5)]
