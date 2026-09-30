"""Social life of the account: answer conversations in context, make friends, live in the tribe, reach out.

Never with the other accounts run here, never in bulk, every text written by the model from real data.
"""

from typing import Any

from loguru import logger

from tribal_assistant.core.agents.coordination.proposal import Factors, Horizon, Proposal
from tribal_assistant.core.agents.coordination.view import CoordinationView
from tribal_assistant.core.agents.knobs import knob_int
from tribal_assistant.core.agents.proposers.base import Proposer
from tribal_assistant.core.agents.proposers.diplomacy import PENDING, lead
from tribal_assistant.core.agents.social.ledger import FRIENDS, TRIBE_MEMBERS, SocialLedger
from tribal_assistant.core.agents.social.rules import SocialRules, same
from tribal_assistant.core.agents.social.writer import SocialWriter

RETRY = "pendente"


class SocialProposer(Proposer):
    key = "social"
    title = "Social"
    observes = "caixa de entrada, pedidos de amizade, fórum da tribo e vizinhos ativos"
    delivers = "conversas respondidas com contexto, amizades, apresentação na tribo e contatos novos, sem spam"

    def __init__(self, writer: SocialWriter | None = None) -> None:
        self.writer = writer or SocialWriter()

    async def propose(self, view: CoordinationView) -> list[Proposal]:
        if view.dry_run or not lead(view):
            return []

        items: list[Proposal] = []
        for step in (self._inbox, self._friends, self._tribe, self._outreach):
            try:
                items += await step(view)
            except Exception as exc:
                view.note_error = str(exc)
                logger.warning("Passo social {} falhou: {}", step.__name__, exc)
        return items

    def _proposal(self, action: str, arguments: dict[str, Any], reason: str, benefit: str, urgency: float, impact: float) -> Proposal:
        return Proposal(
            self.key,
            action,
            {**arguments, "reason": reason[:60]},
            reason,
            benefit,
            factors=Factors(urgency=urgency, impact=impact, opportunity=0.5),
            horizon=Horizon.STRATEGIC,
            confidence=0.7,
        )

    @staticmethod
    def me(view: CoordinationView) -> str:
        return str((view.ctx.player or {}).get("name") or "")

    async def facts(self, view: CoordinationView, ledger: SocialLedger) -> dict[str, Any]:
        return await ledger.facts(view.ctx.player, len(view.siblings) or 1, view.role.value)

    @staticmethod
    def worth_opening(mail: dict[str, Any], stored: dict[str, Any]) -> bool:
        decision = (stored.get("decision") or {}).get("what")
        return bool(mail.get("unread")) or not stored or decision in (None, RETRY)

    async def _inbox(self, view: CoordinationView) -> list[Proposal]:
        if not await view.cooldown("mail"):
            return []

        ledger = SocialLedger(view.session)
        me, managed = self.me(view), await ledger.managed()
        facts: dict[str, Any] | None = None
        opened, items = 0, []
        for mail in await view.actions.social.inbox(view.ctx.game_id):
            if len(items) >= knob_int(view, "social.replies_per_round") or opened >= knob_int(view, "social.threads_per_round"):
                break

            stored = await ledger.thread(mail["id"])
            if SocialRules.system(mail):
                if not stored:
                    await ledger.save_thread(mail, {"messages": []}, {"intent": "sistema", "category": "ignore"})
                    await ledger.decide(mail["id"], "ignorada", "mensagem do sistema")
                continue

            if not self.worth_opening(mail, stored):
                continue

            opened += 1
            thread = await view.actions.social.thread(view.ctx.game_id, mail["id"])
            if facts is None:
                facts = await self.facts(view, ledger)
            proposal = await self.answer(view, ledger, mail, thread, stored, me, managed, facts)
            if proposal is not None:
                items.append(proposal)
        return items

    async def answer(
        self,
        view: CoordinationView,
        ledger: SocialLedger,
        mail: dict[str, Any],
        thread: dict[str, Any],
        stored: dict[str, Any],
        me: str,
        managed: set[str],
        facts: dict[str, Any],
    ) -> Proposal | None:
        """Read the whole conversation, file it with who the other player is, and decide whether and what to answer."""
        messages = thread.get("messages") or []
        conversation = " ".join(m.get("text", "") for m in messages)
        card = await ledger.card(str(mail.get("sender") or ""), view.ctx.player, view.knobs)
        category, why = SocialRules.classify(mail, conversation, me=me, managed=managed, card=card)
        intent = SocialRules.intent(" ".join(m.get("text", "") for m in messages[-2:]) or str(mail.get("subject", "")))

        theirs = [m for m in messages if not same(m.get("author"), me)]
        if category != "ignore" and len(theirs) > int(stored.get("theirs") or 0):
            await ledger.record_heard(str(mail["sender"]), mail.get("sender_id"))

        await ledger.save_thread(mail, {"messages": messages}, {"intent": intent, "category": category, "card": card, "theirs": len(theirs), "who": SocialLedger.label(card)})
        if category == "ignore":
            await ledger.decide(mail["id"], "ignorada", why)
            return None

        if not SocialRules.pending(messages, me):
            await ledger.decide(mail["id"], "sem pendência", "a última mensagem é nossa")
            return None

        written = await self.writer.reply(facts, card, {**thread, "subject": mail.get("subject")}, intent, knob_int(view, "social.history_messages"))
        if written.text is None:
            unavailable = written.skipped == "IA indisponível"
            await ledger.decide(mail["id"], RETRY if unavailable else "não respondida", written.skipped or "")
            return None

        await ledger.decide(mail["id"], RETRY, "resposta proposta")
        urgency = 0.6 if category in ("leader", "mentor", "support", "threat", "invite") else 0.4
        return self._proposal(
            "reply_mail",
            {"mail_id": str(mail["id"]), "text": written.text},
            f"responder {mail.get('sender')} ({category})",
            f"conversa com {SocialLedger.label(card)} em dia",
            urgency,
            0.4,
        )

    async def _friends(self, view: CoordinationView) -> list[Proposal]:
        if not await view.cooldown("buddies"):
            return []

        ledger = SocialLedger(view.session)
        me, managed = self.me(view), await ledger.managed()
        found = await view.actions.social.buddies(view.ctx.game_id)
        friends, outgoing = found["friends"], found["outgoing"]
        await ledger.note(FRIENDS, "amigos", f"{len(friends)} amigo(s)", {"count": len(friends), "names": [f["name"] for f in friends], "outgoing": [o["name"] for o in outgoing]})

        def own(name: str) -> bool:
            return same(name, me) or any(same(name, other) for other in managed)

        items = [
            self._proposal("accept_friend", {"buddy_id": str(r["id"]), "name": r["name"]}, f"pedido de amizade de {r['name']}", "amizade para a conquista Amigo fiel", 0.4, 0.3)
            for r in found["incoming"]
            if not own(r["name"])
        ]

        if len(friends) + len(outgoing) + len(items) >= knob_int(view, "social.friend_target") or not await view.cooldown("friend_request"):
            return items

        known = {n["name"] for n in friends + outgoing + found["incoming"]}
        members = sorted((await ledger.get(TRIBE_MEMBERS)).get("members") or [], key=lambda m: -int(m.get("points") or 0))
        candidates = [(m["name"], "colega de tribo") for m in members]
        candidates += [(n["name"], f"vizinho ativo a {n['distance']} campos") for n in await ledger.active_neighbours(view.knobs, managed | {me})]
        pick = next(((name, why) for name, why in candidates if not own(name) and not any(same(name, k) for k in known)), None)
        if pick is None:
            return items

        name, why = pick
        return [*items, self._proposal("add_friend", {"name": name}, f"amizade: {why}", "amizade para a conquista Amigo fiel", 0.2, 0.3)]

    async def _tribe(self, view: CoordinationView) -> list[Proposal]:
        ally_id = (view.ctx.player or {}).get("ally_id")
        if not ally_id or not await view.cooldown("tribe_read"):
            return []

        ledger = SocialLedger(view.session)
        found = await view.actions.tribe.read(view.ctx.game_id, knob_int(view, "diplomacy.forums_read"))
        members, threads = found["members"], found["threads"]
        await ledger.save_tribe("overview", "anúncios e visão geral da tribo", found["overview"], {"ally_id": ally_id})
        await ledger.save_tribe("members", "membros da tribo", ", ".join(m["name"] for m in members), {"members": members})
        await ledger.save_tribe("forum", "tópicos do fórum da tribo", "\n".join(t["title"] for t in threads), {"threads": threads})

        intro = next((t for t in threads if t.get("intro")), None)
        if intro is None or (await ledger.get(f"forum:{intro['id']}")).get("done") or (await ledger.get(f"forum_intro:{ally_id}")).get("done"):
            return []

        tag = await ledger.tribe_tag(ally_id)
        written = await self.writer.forum_intro(await self.facts(view, ledger), {"tag": tag, "membros": len(members)}, intro["title"])
        if written.text is None:
            return []

        return [
            self._proposal(
                "reply_forum",
                {"thread_id": str(intro["id"]), "forum_id": str(intro.get("forum_id") or ""), "text": written.text},
                f"apresentação no tópico {intro['title'][:30]}",
                "entrada na tribo registrada no fórum",
                0.4,
                0.4,
            )
        ]

    async def _outreach(self, view: CoordinationView) -> list[Proposal]:
        if not await view.cooldown("outreach"):
            return []

        ledger = SocialLedger(view.session)
        if await ledger.first_contacts_since(24) >= knob_int(view, "social.first_contacts_per_day"):
            return []

        me, managed = self.me(view), await ledger.managed()
        targets: list[tuple[str, str, str]] = []
        for application in await ledger.applications():
            if application.get("status") != PENDING:
                continue
            leader = await ledger.top_member(str(application.get("ally_id")))
            if leader is not None:
                targets.append((leader.name, "intro_leader", f"candidatura enviada à tribo {application.get('tag')}"))
        targets += [(n["name"], "intro_neighbour", f"vizinho ativo a {n['distance']} campos") for n in await ledger.active_neighbours(view.knobs, managed | {me})]

        for name, kind, reason in targets:
            if same(name, me) or any(same(name, other) for other in managed) or await ledger.contact(name):
                continue

            card = await ledger.card(name, view.ctx.player, view.knobs)
            written = await self.writer.intro(await self.facts(view, ledger), card, reason)
            if written.text is None or written.subject is None:
                logger.info("Apresentação a {} não escrita: {}", name, written.skipped)
                return []

            return [self._proposal("send_mail", {"to": name, "subject": written.subject, "text": written.text, "kind": kind}, reason, "contato novo com quem importa por perto", 0.2, 0.3)]
        return []
