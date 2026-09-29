"""HTTP client for the Tribal Assistant API: the only way the MCP server reaches the engine."""

import os
from typing import Any

import httpx

DEFAULT_URL = "http://127.0.0.1:8000"


class ApiError(RuntimeError):
    pass


class ApiClient:
    """Talks to /api/v1 of a running server; the account comes from TRIBAL_ACCOUNT."""

    def __init__(
        self,
        base_url: str | None = None,
        account: str | None = None,
        timeout: float = 600.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.transport = transport
        self.base_url = (base_url or os.environ.get("TRIBAL_API_URL") or DEFAULT_URL).rstrip("/")
        self.account = account if account is not None else os.environ.get("TRIBAL_ACCOUNT", "")
        self.timeout = timeout

    def headers(self) -> dict[str, str]:
        return {"x-account": self.account} if self.account else {}

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.base_url}/api/v1{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers(), transport=self.transport) as client:
                response = await client.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            raise ApiError(f"API indisponível em {self.base_url}: suba o servidor (tribal-assistant serve). {exc}") from exc

        if response.status_code >= 400:
            raise ApiError(self.error(response))

        if response.status_code == 204 or not response.content:
            return None

        if response.headers.get("content-type", "").startswith("application/json"):
            return response.json()

        return response.text

    @staticmethod
    def error(response: httpx.Response) -> str:
        try:
            detail = response.json().get("detail")
        except ValueError:
            return f"HTTP {response.status_code}: {response.text[:200]}"

        if isinstance(detail, dict):
            return detail.get("message") or str(detail)
        if isinstance(detail, list):
            return "; ".join(str(d.get("msg", d)) for d in detail)

        return str(detail or f"HTTP {response.status_code}")

    async def get(self, path: str, **params: Any) -> Any:
        return await self.request("GET", path, params={k: v for k, v in params.items() if v is not None})

    async def post(self, path: str, body: Any = None) -> Any:
        return await self.request("POST", path, json=body)

    async def patch(self, path: str, body: Any) -> Any:
        return await self.request("PATCH", path, json=body)

    async def put(self, path: str, body: Any) -> Any:
        return await self.request("PUT", path, json=body)

    async def delete(self, path: str) -> Any:
        return await self.request("DELETE", path)
