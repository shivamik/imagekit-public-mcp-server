from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.client import ImageKitClient, SearchDocsResponse, TransformResponse


@pytest.fixture
def client():
    return ImageKitClient()


@pytest.mark.asyncio
async def test_search_docs(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": "Found 3 docs about uploads"}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        result = await client.search_docs("upload files")
        assert isinstance(result, SearchDocsResponse)
        assert result.results == "Found 3 docs about uploads"


@pytest.mark.asyncio
async def test_transform(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "url": "https://ik.imagekit.io/demo/tr:w-300,h-200/image.jpg",
        "tr_value": "w-300,h-200",
        "status": "success",
        "message": "Transformation applied successfully",
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        result = await client.transform(
            "resize to 300x200", src="https://ik.imagekit.io/demo/image.jpg"
        )
        assert isinstance(result, TransformResponse)
        assert result.status == "success"
        assert result.tr_value == "w-300,h-200"
