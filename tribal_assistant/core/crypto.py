"""Encrypts stored game passwords with a key from APP_SECRET or a local key file."""

from pathlib import Path

from cryptography.fernet import Fernet

from tribal_assistant.core.config import settings


class Vault:
    def __init__(self, secret: str | None = None, key_file: str = "./storage/secret.key") -> None:
        self.key_file = Path(key_file)
        self.fernet = Fernet(secret.encode() if secret else self._key())

    def _key(self) -> bytes:
        if self.key_file.exists():
            return self.key_file.read_bytes().strip()

        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        key = Fernet.generate_key()
        self.key_file.write_bytes(key)
        self.key_file.chmod(0o600)
        return key

    def encrypt(self, value: str) -> str:
        return self.fernet.encrypt(value.encode()).decode()

    def decrypt(self, token: str) -> str:
        return self.fernet.decrypt(token.encode()).decode()


def vault() -> Vault:
    return Vault(settings.app_secret)
