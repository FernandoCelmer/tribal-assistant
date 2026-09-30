"""Texts for other players, written by the configured model from real game data and checked before they go out."""

import json
from dataclasses import dataclass
from typing import Any

from loguru import logger

from tribal_assistant.core.agents.social.rules import SocialRules
from tribal_assistant.core.agents.writer import ModelWriter

MAX_CHARS = 800
SUBJECT_CHARS = 60
CAN_NOT = "esta conta não envia tropas, apoio nem recursos para outros jogadores e não aceita sitter nem conta compartilhada"

SYSTEM = (
    "Você escreve mensagens de um jogador de Tribal Wars (servidor brasileiro) para outros jogadores, em português do Brasil, "
    "tom cordial e natural, de 1 a 4 frases curtas. Regras: use só os fatos, a ficha do outro jogador e o histórico informados; "
    "nunca invente números, conquistas, alianças ou decisões; não repita números que não estejam nos dados. "
    "Nunca prometa enviar tropas, apoio ou recursos; se pedirem apoio, diga com honestidade o que a conta pode fazer. "
    "Nunca compartilhe e-mail, senha ou dados da conta e nunca aceite sitter ou conta compartilhada. "
    "Se perguntarem se você é um bot ou automatizado, responda de forma neutra e curta, sem afirmar ser humano e sem mentir. "
    "Sem links, sem contato fora do jogo, sem emojis, sem hashtags. "
    "Se não houver nada útil a dizer, responda só 'IGNORAR: <motivo curto>'."
)


@dataclass
class Written:
    text: str | None = None
    subject: str | None = None
    skipped: str | None = None


class SocialWriter(ModelWriter):
    @staticmethod
    def limits(facts: dict[str, Any]) -> dict[str, Any]:
        return {**facts, "limites": CAN_NOT}

    @staticmethod
    def dump(data: Any) -> str:
        return json.dumps(data, ensure_ascii=False, default=str)

    @staticmethod
    def transcript(thread: dict[str, Any], limit: int) -> str:
        messages = (thread.get("messages") or [])[-limit:]
        return "\n".join(f"[{m.get('date') or '-'}] {m.get('author') or '?'}: {m.get('text', '')}" for m in messages)

    @staticmethod
    def clean(text: str) -> str:
        return " ".join(text.replace('"', "").split()).strip()[:MAX_CHARS]

    def checked(self, raw: str | None, sources: str, purpose: str) -> Written:
        if raw is None:
            return Written(skipped="IA indisponível")

        skipped = SocialRules.skipped(raw)
        if skipped:
            return Written(skipped=skipped)

        text = self.clean(raw)
        if len(text) < 5:
            return Written(skipped="texto vazio")

        refusal = SocialRules.refusal(text, sources)
        if refusal:
            logger.warning("Texto de {} descartado: {}", purpose, refusal)
            return Written(skipped=f"descartado: {refusal}")

        return Written(text=text)

    async def reply(self, facts: dict[str, Any], card: dict[str, Any], thread: dict[str, Any], intent: str, history: int) -> Written:
        conversation = self.transcript(thread, history)
        flags = SocialRules.flags(conversation)
        prompt = (
            f"Meus dados e decisões reais: {self.dump(self.limits(facts))}\n"
            f"Ficha do outro jogador: {self.dump(card)}\n"
            f"Intenção percebida: {intent}; sinais: {self.dump(flags)}\n"
            f"Assunto: {thread.get('subject', '')}\n"
            f"Conversa completa (mais antiga primeiro):\n{conversation}\n\n"
            "Leia a conversa inteira e decida: escreva a resposta à última mensagem, coerente com as decisões reais, "
            "ou 'IGNORAR: <motivo>' se não valer responder."
        )
        return self.checked(await self.ask(SYSTEM, prompt, "a resposta"), self.sources(facts, card, conversation, thread.get("subject", "")), "resposta")

    async def application(self, facts: dict[str, Any], tribe: dict[str, Any]) -> Written:
        prompt = (
            f"Meus dados: {self.dump(self.limits(facts))}\nTribo: {self.dump(tribe)}\n"
            "Escreva a candidatura para entrar nessa tribo: quem sou, como jogo e o que posso somar, sem exageros."
        )
        return self.checked(await self.ask(SYSTEM, prompt, "a candidatura"), self.sources(facts, tribe), "candidatura")

    async def intro(self, facts: dict[str, Any], card: dict[str, Any], reason: str) -> Written:
        prompt = (
            f"Meus dados: {self.dump(self.limits(facts))}\nFicha do outro jogador: {self.dump(card)}\nMotivo do contato: {reason}\n"
            "Escreva a primeira mensagem de apresentação, curta, sem pedir recursos nem tropas. "
            "Responda em duas linhas: 'ASSUNTO: <até 6 palavras>' e 'TEXTO: <mensagem>'."
        )
        raw = await self.ask(SYSTEM, prompt, "a apresentação")
        subject, text = self.split(raw)
        written = self.checked(text, self.sources(facts, card, reason), "apresentação")
        if written.text is None:
            return written
        if not subject or SocialRules.refusal(subject, self.sources(facts, card, reason)):
            return Written(skipped="assunto ausente ou inválido")
        written.subject = subject[:SUBJECT_CHARS]
        return written

    async def forum_intro(self, facts: dict[str, Any], tribe: dict[str, Any], thread: str) -> Written:
        prompt = (
            f"Meus dados: {self.dump(self.limits(facts))}\nTribo: {self.dump(tribe)}\nTópico: {thread}\n"
            "Escreva uma apresentação curta para esse tópico do fórum da tribo, agradecendo a entrada."
        )
        return self.checked(await self.ask(SYSTEM, prompt, "a apresentação no fórum"), self.sources(facts, tribe, thread), "fórum")

    @staticmethod
    def sources(*parts: Any) -> str:
        return " ".join(p if isinstance(p, str) else json.dumps(p, ensure_ascii=False, default=str) for p in parts)

    @staticmethod
    def split(raw: str | None) -> tuple[str | None, str | None]:
        if raw is None:
            return None, None
        if SocialRules.skipped(raw):
            return None, raw
        subject, text = None, []
        for line in raw.splitlines():
            head = line.strip()
            if head.upper().startswith("ASSUNTO:"):
                subject = SocialWriter.clean(head.split(":", 1)[1])
            elif head.upper().startswith("TEXTO:"):
                text.append(head.split(":", 1)[1])
            elif text:
                text.append(head)
        return subject, " ".join(text) or None
