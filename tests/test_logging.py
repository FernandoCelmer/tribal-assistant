from loguru import logger

from tribal_assistant.core.logging import LoggingSetup


class FakeStore:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def sink(self, message) -> None:
        self.messages.append(message.record["message"])


def test_database_sink_survives_a_second_configure(monkeypatch) -> None:
    store = FakeStore()
    monkeypatch.setattr(LoggingSetup, "store", store)

    LoggingSetup.configure("INFO")
    LoggingSetup.configure("INFO")
    logger.info("depois de configurar duas vezes")

    assert store.messages.count("depois de configurar duas vezes") == 1
    logger.remove()
