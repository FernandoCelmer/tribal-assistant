from tribal_assistant.core.game.items import ItemCount


def test_item_is_consumed_only_when_the_owned_count_drops() -> None:
    assert ItemCount.of("Pacote de recurso (1%) Consumível Da propriedade de:3 Usar") == 3
    assert ItemCount.consumed(1, 0)
    assert ItemCount.consumed(3, 2)
    assert not ItemCount.consumed(1, 1)
