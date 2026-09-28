from pydantic import BaseModel


class BotStatus(BaseModel):
    running: bool
    logged_in: bool
    world: str
    scheduler_jobs: list[str] = []


class BotCommandResult(BaseModel):
    ok: bool
    message: str
