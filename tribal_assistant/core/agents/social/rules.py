"""What a message is about, whether it deserves an answer, and whether a text is safe to send."""

import re
from typing import Any

SYSTEM = re.compile(r"equipe tribal wars|innogames|^sistema$|^tribal wars$", re.I)
NEGATION = re.compile(r"\b(n[ãa]o|nunca|nem|jamais)\b[^.!?]{0,25}$", re.I)

INTENTS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("spam", re.compile(r"https?://|www\.|discord\.gg|whats\s*app|compre|promo[çc][ãa]o|desconto|sorteio|ganhe (?:pp|pontos premium)|pontos premium gr[áa]tis|clique aqui|\bvendo conta", re.I)),
    ("threat", re.compile(r"vou (?:te )?(?:atacar|nobrar|farmar|destruir|limpar)|sua aldeia (?:é|e|vai ser) minha|se prepara|vai perder (?:a|sua) aldeia|nobrar voc", re.I)),
    ("support", re.compile(r"\bapoi[oa]r?\b|ajuda (?:com|na) (?:tropa|defesa)|mand[ae]r? (?:tropa|defesa)|preciso de (?:tropa|defesa)|me defende", re.I)),
    ("invite", re.compile(r"convite|convidar|recrut|entr(?:a|e|ar) (?:na|pra|para a) (?:nossa )?tribo|junte-se|candidat", re.I)),
    ("diplomacy", re.compile(r"\bnap\b|pacto|n[ãa]o[- ]agress|alian[çc]a|acordo|tr[ée]gua|paz\b", re.I)),
    ("trade", re.compile(r"\btroca|com[ée]rcio|mercado|recursos?|madeira|argila|ferro\b", re.I)),
    ("question", re.compile(r"\?|\bcomo\b|\bquando\b|\bonde\b|\bqual\b|\bquem\b|\bpor ?que\b", re.I)),
)

ASKS_BOT = re.compile(r"\b(bot|rob[ôo]|script|automatizad\w*|autom[áa]tic\w*|macro)\b", re.I)
ASKS_ACCOUNT = re.compile(r"senha|e-?mail|sitter|substitut\w*|compartilh\w* (?:a |sua )?conta|dados da conta|\blogin\b", re.I)

LINK = re.compile(r"https?://|www\.|\b[\w-]+\.(?:com|net|org|gg|io)(?:\.br)?\b", re.I)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
SECRET = re.compile(r"(?:minha|a) senha (?:é|e)\b|meu (?:login|e-?mail) (?:é|e)\b", re.I)
HUMAN = re.compile(r"n[ãa]o sou (?:um |uma )?(?:bot|rob[ôo]|m[áa]quina|programa|script)|sou (?:um |uma )?(?:humano|pessoa real|pessoa de verdade|jogador de verdade)", re.I)
PROMISE = re.compile(r"\b(?:vou|irei|vamos|mando|envio|enviarei|mandarei|posso mandar|posso enviar|te mando|te envio)\b[^.!?]{0,40}\b(?:tropas?|apoio|defesa|recursos?|madeira|argila|ferro)\b", re.I)
SITTER = re.compile(r"\b(?:aceito|pode ser|topo|claro|combinado)\b[^.!?]{0,30}\b(?:sitter|substitut\w*|compartilh\w*)", re.I)
NUMBER = re.compile(r"\d[\d.]*")
IGNORE = re.compile(r"^\s*IGNORAR\b[:\s-]*(.*)$", re.I | re.S)

REPLY_WORTHY = ("leader", "mentor", "tribe", "invite", "support", "diplomacy", "question", "trade", "threat", "chat")


def same(a: str | None, b: str | None) -> bool:
    return bool(a and b) and str(a).strip().casefold() == str(b).strip().casefold()


class SocialRules:
    @staticmethod
    def intent(text: str) -> str:
        for name, pattern in INTENTS:
            if pattern.search(text):
                return name
        return "chat"

    @staticmethod
    def system(mail: dict[str, Any]) -> bool:
        return bool(mail.get("system")) or not mail.get("sender") or bool(SYSTEM.search(str(mail.get("sender", ""))))

    @classmethod
    def classify(cls, mail: dict[str, Any], text: str, *, me: str, managed: set[str], card: dict[str, Any]) -> tuple[str, str]:
        """(category, why). Category "ignore" means no answer; every other category deserves one."""
        sender = str(mail.get("sender") or "")
        if cls.system(mail):
            return "ignore", "mensagem do sistema"
        if same(sender, me):
            return "ignore", "mensagem da própria conta"
        if any(same(sender, name) for name in managed):
            return "ignore", "conta administrada por este app"

        intent = cls.intent(f"{mail.get('subject', '')} {text}")
        if intent == "spam":
            return "ignore", "propaganda ou spam"
        if card.get("mentor"):
            return "mentor", intent
        if card.get("leader"):
            return "leader", intent
        if card.get("same_tribe") and intent == "chat":
            return "tribe", intent
        return intent, intent

    @staticmethod
    def pending(messages: list[dict[str, Any]], me: str) -> bool:
        """The last word in the conversation is someone else's."""
        if not messages:
            return False
        last = messages[-1]
        return bool(last.get("text")) and not same(last.get("author"), me)

    @staticmethod
    def flags(text: str) -> dict[str, bool]:
        return {"asks_bot": bool(ASKS_BOT.search(text)), "asks_account": bool(ASKS_ACCOUNT.search(text))}

    @staticmethod
    def numbers(text: str) -> set[str]:
        return {n.replace(".", "").rstrip(".") for n in NUMBER.findall(text)}

    @staticmethod
    def _affirmed(pattern: re.Pattern[str], text: str) -> bool:
        return any(not NEGATION.search(text[: m.start()]) for m in pattern.finditer(text))

    @classmethod
    def refusal(cls, text: str, sources: str | None = None) -> str | None:
        """Why a written text must not go out, or None when it is safe."""
        if LINK.search(text) or EMAIL.search(text):
            return "texto com link ou e-mail"
        if SECRET.search(text):
            return "texto com dado de conta"
        if HUMAN.search(text):
            return "texto afirma ser humano"
        if cls._affirmed(PROMISE, text):
            return "texto promete tropas ou recursos"
        if cls._affirmed(SITTER, text):
            return "texto aceita sitter ou conta compartilhada"
        if sources is None:
            return None
        invented = cls.numbers(text) - cls.numbers(sources)
        if invented:
            return f"texto com número fora dos fatos: {', '.join(sorted(invented))}"
        return None

    @staticmethod
    def skipped(text: str) -> str | None:
        """The model's own decision not to answer, with its reason."""
        found = IGNORE.match(text or "")
        return (found.group(1).strip() or "a IA decidiu não responder") if found else None

    @staticmethod
    def recipients(to: str) -> list[str]:
        return [name.strip() for name in re.split(r"[;,\n]", to) if name.strip()]
