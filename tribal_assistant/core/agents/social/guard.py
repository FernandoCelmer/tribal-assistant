"""Every text to another player passes here: one recipient, never an own account, within the hourly and daily limits."""

from sqlalchemy.ext.asyncio import AsyncSession

from tribal_assistant.core.agents.knobs import Knobs
from tribal_assistant.core.agents.social.ledger import SocialLedger
from tribal_assistant.core.agents.social.rules import SocialRules, same


class SocialGuard:
    def __init__(self, session: AsyncSession, knobs: Knobs) -> None:
        self.ledger = SocialLedger(session)
        self.knobs = knobs

    async def text(self, text: str) -> str | None:
        refusal = SocialRules.refusal(text)
        if refusal:
            return refusal

        cap = self.knobs.int("social.messages_per_hour")
        if await self.ledger.sent_since(self.knobs.get("social.send_window_hours")) >= cap:
            return f"limite de {cap} mensagens por hora"
        return None

    async def player(self, recipient: str, me: str | None) -> str | None:
        names = SocialRules.recipients(recipient)
        if len(names) != 1:
            return "cada mensagem vai para um único jogador, nunca em massa"

        name = names[0]
        if same(name, me):
            return "destinatário é a própria conta"
        if any(same(name, other) for other in await self.ledger.managed()):
            return "destinatário é uma conta administrada por este app"
        return None

    async def first_contact(self, recipient: str) -> str | None:
        contact = await self.ledger.contact(recipient)
        if contact.get("heard"):
            return None
        if contact.get("sent"):
            return "jogador já contatado e ainda sem resposta"

        daily = self.knobs.int("social.first_contacts_per_day")
        if await self.ledger.first_contacts_since(self.knobs.get("social.first_contact_window_hours")) >= daily:
            return f"limite de {daily} primeiros contatos por dia"
        return None

    async def check(self, recipient: str, text: str, me: str | None, first: bool) -> str | None:
        return await self.player(recipient, me) or (await self.first_contact(recipient) if first else None) or await self.text(text)
