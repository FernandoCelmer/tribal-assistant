"""CLI entrypoint. Runs the API server."""

import uvicorn

from app.core.config import settings


def main() -> None:
    uvicorn.run(
        "app:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
    )


if __name__ == "__main__":
    main()
