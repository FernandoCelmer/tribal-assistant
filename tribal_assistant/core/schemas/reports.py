from pydantic import BaseModel

from tribal_assistant.core.schemas.game import ReportOut


class ReportPage(BaseModel):
    total: int
    offset: int
    limit: int
    items: list[ReportOut]
