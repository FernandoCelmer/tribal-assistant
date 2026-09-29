"""Translates core domain errors into one JSON error shape."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from tribal_assistant.core.errors import DomainError


def install_error_handlers(application: FastAPI) -> None:
    @application.exception_handler(DomainError)
    async def _handle(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.as_detail()})
