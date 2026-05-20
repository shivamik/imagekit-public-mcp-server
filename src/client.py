from dataclasses import dataclass

import httpx

from .config import config


@dataclass
class SearchDocsResponse:
    results: str


@dataclass
class TransformResponse:
    url: str | None
    tr_value: str | None
    status: str
    message: str


class ImageKitClient:
    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=config.IMAGEKIT_API_BASE_URL,
                headers={"Host": config.IMAGEKIT_API_HOST},
                timeout=30.0,
            )
        return self._client

    async def search_docs(self, query: str, sources: list[str] | None = None) -> SearchDocsResponse:
        client = await self._get_client()
        params: dict = {"query": query}
        if sources:
            params["sources"] = sources
        response = await client.get("/mcp/search_docs", params=params)
        response.raise_for_status()
        data = response.json()
        return SearchDocsResponse(results=data["results"])

    async def transform(
        self,
        query: str,
        src: str | None = None,
        fetch_url_to_check: bool = True,
    ) -> TransformResponse:
        client = await self._get_client()
        params: dict = {"query": query, "fetch_url_to_check": str(fetch_url_to_check).lower()}
        if src:
            params["src"] = src
        response = await client.get("/mcp/transform", params=params)
        response.raise_for_status()
        data = response.json()
        return TransformResponse(
            url=data.get("url"),
            tr_value=data.get("tr_value"),
            status=data["status"],
            message=data["message"],
        )

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


imagekit_client = ImageKitClient()
