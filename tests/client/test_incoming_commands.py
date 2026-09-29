from datetime import UTC, datetime

from tribal_assistant.core.game.incoming import IncomingLabel
from tribal_assistant.core.game.scraper.game import parse_commands

ROWS = [
    {"direction": "in", "id": "77", "icon": "https://cdn/graphic/command/attack_medium.webp",
     "hint": "Ataque médio (1000-5000 tropas)", "type": "attack", "origin": "Aldeia do Vizinho (480|750) K74",
     "player": " Vizinho ", "watchtower": True, "text": "Ataque", "end": "1790709103"},
    {"direction": "in", "id": "78", "icon": "graphic/command/snob.png", "text": "Ataque", "end": "1790709200"},
    {"direction": "out", "id": "253749823", "icon": "https://cdn/graphic/command/return_attack_small.webp",
     "hint": "Ataque pequeno (1-1000 tropas) (retornando)", "type": "return",
     "text": "Retorno de Aldeia-bonus (487|752) K74", "end": "1790710861"},
]


def test_incoming_keeps_origin_player_size_and_watchtower() -> None:
    attack, noble, _ = parse_commands(ROWS)

    assert (attack.kind, attack.coords, attack.origin_coords, attack.origin_player) == ("attack", "480|750", "480|750", "Vizinho")
    assert (attack.size, attack.watchtower) == ("medium", True)
    assert IncomingLabel.parse(attack.label)["player"] == "Vizinho"
    assert attack.arrival_at == datetime.fromtimestamp(1790709103, UTC)

    assert noble.kind == "noble" and noble.label == "Ataque" and noble.coords is None


def test_returning_small_attack_is_a_return_not_an_attack() -> None:
    back = parse_commands(ROWS)[2]

    assert (back.direction, back.kind, back.coords, back.size) == ("out", "return", "487|752", None)
    assert back.label == "Retorno de Aldeia-bonus (487|752) K74"
