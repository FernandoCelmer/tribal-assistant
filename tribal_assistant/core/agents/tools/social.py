"""Social tools: inbox, conversations, replies, friends and the tribe forum, always behind the social guard."""

from typing import TYPE_CHECKING, Any, ClassVar

from tribal_assistant.core.agents.knobs import knob_int, tuning
from tribal_assistant.core.agents.social.guard import SocialGuard
from tribal_assistant.core.agents.social.ledger import FRIENDS, SocialLedger
from tribal_assistant.core.agents.tools.base import AgentTool, ToolOutcome

if TYPE_CHECKING:
    from tribal_assistant.core.agents.toolbox import Toolbox

REASON = {"type": "string", "description": "Motivo curto (até 8 palavras), registrado no log."}
TEXT = {"type": "string", "minLength": 5, "maxLength": 800, "description": "Texto escrito a partir de fatos reais do jogo."}


def me(box: "Toolbox") -> str | None:
    return (box.ctx.player or {}).get("name")


class ReadInbox(AgentTool):
    name = "read_inbox"
    description = "Lê a caixa de entrada do jogo: id, assunto, remetente, data, se é não lida e se é do sistema."

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        mails = await box.actions.social.inbox(box.ctx.game_id)
        return ToolOutcome(True, self.dump(mails) if mails else "caixa de entrada vazia", {"mails": len(mails)})


class ReadThread(AgentTool):
    name = "read_thread"
    description = (
        "Conversas guardadas no banco: sem mail_id lista as recentes (assunto, remetente, intenção, decisão); "
        "com mail_id traz a conversa inteira, a ficha do outro jogador e o que foi decidido."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {"mail_id": {"type": "string", "pattern": "^[0-9]+$"}},
        "additionalProperties": False,
    }

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        ledger = SocialLedger(box.session)
        if args.get("mail_id"):
            thread = await ledger.thread(str(args["mail_id"]))
            return ToolOutcome(bool(thread), self.dump(thread) if thread else "conversa não encontrada no banco")

        threads = [
            {k: t.get(k) for k in ("id", "subject", "sender", "date", "intent", "category", "decision")}
            for t in await ledger.threads()
        ]
        return ToolOutcome(True, self.dump(threads) if threads else "nenhuma conversa guardada")


class ReplyMail(AgentTool):
    name = "reply_mail"
    description = "Responde uma conversa da caixa de entrada. Nunca a contas deste app, nunca em massa, dentro do limite por hora."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {"mail_id": {"type": "string", "pattern": "^[0-9]+$"}, "text": TEXT, "reason": REASON},
        "required": ["mail_id", "text", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        ledger = SocialLedger(box.session)
        mail_id, text = str(args["mail_id"]), str(args["text"]).strip()
        thread = await ledger.thread(mail_id)
        sender = str(thread.get("sender") or "")
        if not sender or thread.get("system"):
            return ToolOutcome(False, "RECUSADO: conversa desconhecida ou do sistema")

        refusal = await SocialGuard(box.session, tuning(box.ctx)).check(sender, text, me(box), first=False)
        if refusal:
            return ToolOutcome(False, f"RECUSADO: {refusal}")

        if box.dry_run:
            return ToolOutcome(True, f"(simulação) responder a {sender}")

        result = await box.actions.social.reply(box.ctx.game_id, mail_id, text)
        if result.ok:
            await ledger.record_sent(sender, "reply", thread.get("sender_id"))
            await ledger.decide(mail_id, "respondida", str(args.get("reason", "")))
        return ToolOutcome(result.ok, result.detail, result.data)


class SendMail(AgentTool):
    name = "send_mail"
    description = (
        "Escreve uma mensagem nova para UM jogador (apresentação ou contato). Recusado para contas deste app, "
        "para quem já foi contatado sem responder e acima dos limites por hora e por dia."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "to": {"type": "string", "minLength": 2, "maxLength": 40},
            "subject": {"type": "string", "minLength": 2, "maxLength": 60},
            "text": TEXT,
            "kind": {"type": "string", "enum": ["intro_neighbour", "intro_leader", "contact"]},
            "reason": REASON,
        },
        "required": ["to", "subject", "text", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        to, subject, text = str(args["to"]).strip(), str(args["subject"]).strip(), str(args["text"]).strip()
        guard = SocialGuard(box.session, tuning(box.ctx))
        refusal = await guard.check(to, f"{subject}. {text}", me(box), first=True)
        if refusal:
            return ToolOutcome(False, f"RECUSADO: {refusal}")

        if box.dry_run:
            return ToolOutcome(True, f"(simulação) mensagem para {to}")

        result = await box.actions.social.send(box.ctx.game_id, to, subject, text)
        if result.ok:
            await guard.ledger.record_sent(to, str(args.get("kind") or "contact"))
        return ToolOutcome(result.ok, result.detail, result.data)


class AcceptFriend(AgentTool):
    name = "accept_friend"
    description = "Aceita um pedido de amizade recebido (nunca de contas deste app)."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {"buddy_id": {"type": "string", "minLength": 1}, "name": {"type": "string"}, "reason": REASON},
        "required": ["buddy_id", "name", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        refusal = await SocialGuard(box.session, tuning(box.ctx)).player(str(args["name"]), me(box))
        if refusal:
            return ToolOutcome(False, f"RECUSADO: {refusal}")

        if box.dry_run:
            return ToolOutcome(True, f"(simulação) aceitar amizade de {args['name']}")

        result = await box.actions.social.accept_buddy(box.ctx.game_id, str(args["buddy_id"]))
        return ToolOutcome(result.ok, result.detail, result.data)


class AddFriend(AgentTool):
    name = "add_friend"
    description = "Pede amizade a UM jogador (colega de tribo ou vizinho ativo), no ritmo e até o alvo de amizades."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {"name": {"type": "string", "minLength": 2, "maxLength": 40}, "reason": REASON},
        "required": ["name", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        name = str(args["name"]).strip()
        guard = SocialGuard(box.session, tuning(box.ctx))
        refusal = await guard.player(name, me(box))
        if refusal:
            return ToolOutcome(False, f"RECUSADO: {refusal}")

        friends = await guard.ledger.get(FRIENDS)
        target = knob_int(box.ctx, "social.friend_target")
        if int(friends.get("count", 0)) + len(friends.get("outgoing", [])) >= target:
            return ToolOutcome(False, f"RECUSADO: alvo de {target} amizades já alcançado ou pedido")

        if box.dry_run:
            return ToolOutcome(True, f"(simulação) pedir amizade a {name}")

        result = await box.actions.social.add_buddy(box.ctx.game_id, name)
        return ToolOutcome(result.ok, result.detail, result.data)


class ReadTribe(AgentTool):
    name = "read_tribe"
    description = "Anúncios, membros e tópicos do fórum da tribo guardados no banco (lidos na última visita)."

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        ledger = SocialLedger(box.session)
        found = {key: await ledger.get(f"tribe:{key}") for key in ("overview", "members", "forum")}
        return ToolOutcome(any(found.values()), self.dump(found) if any(found.values()) else "tribo ainda não lida")


class ReplyForum(AgentTool):
    name = "reply_forum"
    description = "Responde um tópico do fórum da tribo (apresentação ou recrutamento), dentro do limite por hora."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "thread_id": {"type": "string", "pattern": "^[0-9]+$"},
            "forum_id": {"type": "string"},
            "text": TEXT,
            "reason": REASON,
        },
        "required": ["thread_id", "text", "reason"],
        "additionalProperties": False,
    }
    acts = True

    async def run(self, box: "Toolbox", args: dict[str, Any]) -> ToolOutcome:
        if not (box.ctx.player or {}).get("ally_id"):
            return ToolOutcome(False, "RECUSADO: fora de uma tribo")

        text = str(args["text"]).strip()
        refusal = await SocialGuard(box.session, tuning(box.ctx)).text(text)
        if refusal:
            return ToolOutcome(False, f"RECUSADO: {refusal}")

        if box.dry_run:
            return ToolOutcome(True, f"(simulação) responder no tópico {args['thread_id']}")

        thread_id = str(args["thread_id"])
        result = await box.actions.tribe.reply(box.ctx.game_id, thread_id, args.get("forum_id") or None, text)
        if result.ok:
            ledger = SocialLedger(box.session)
            await ledger.note(f"forum:{thread_id}", f"resposta no tópico {thread_id}", text, {"done": True})
            await ledger.note(f"forum_intro:{box.ctx.player['ally_id']}", "apresentação na tribo", thread_id, {"done": True})
        return ToolOutcome(result.ok, result.detail, result.data)
