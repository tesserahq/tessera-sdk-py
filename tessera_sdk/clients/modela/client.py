import json
import logging
from collections.abc import AsyncIterator
from typing import Any, Optional

import httpx
import requests

from ...config import get_settings
from ...constants import HTTPMethods
from .._base.client import BaseClient
from .._base.exceptions import (
    TesseraAuthenticationError,
    TesseraClientError,
    TesseraError,
    TesseraNotFoundError,
    TesseraServerError,
    TesseraValidationError,
)
from .schemas.chat_completion_chunk import ChatCompletionChunk
from .schemas.chat_completion_request import ChatCompletionRequest, CompletionMessage
from .schemas.chat_completion_response import ChatCompletionResponse
from .schemas.scan_file_request import ScanFileRequest
from .schemas.scan_response import ScanResponse
from .schemas.summarize_file_request import SummarizeFileRequest
from .schemas.summarize_response import SummarizeResponse
from .schemas.summarize_text_request import SummarizeTextRequest

logger = logging.getLogger(__name__)


class ModelaClient(BaseClient):
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: Optional[int] = None,
        session: Optional[requests.Session] = None,
    ):
        if base_url is None:
            base_url = get_settings().modela_api_url

        super().__init__(
            base_url=base_url,
            api_token=api_token,
            timeout=timeout,
            session=session,
            service_name="modela",
        )

    def complete(
        self,
        messages: list[CompletionMessage],
        model: Optional[str] = None,
        extra_body: Optional[dict[str, Any]] = None,
        project_id: str = "*",
    ) -> ChatCompletionResponse:
        request = ChatCompletionRequest(
            messages=messages,
            model=model,
            extra_body=extra_body,
        )
        response = self._make_request(
            HTTPMethods.POST,
            "/chat/completions",
            data=request.model_dump(mode="json", exclude_none=True),
            params={"project_id": project_id},
        )
        return ChatCompletionResponse(**response.json())

    async def stream_complete(
        self,
        messages: list[CompletionMessage],
        model: Optional[str] = None,
        extra_body: Optional[dict[str, Any]] = None,
        project_id: str = "*",
    ) -> AsyncIterator[ChatCompletionChunk]:
        """Stream a chat completion from Modela as parsed SSE chunks.

        Uses httpx (async) rather than the sync `requests`-based `_make_request`,
        since streaming a response body isn't supported by the shared BaseClient.
        """
        request = ChatCompletionRequest(
            messages=messages,
            model=model,
            extra_body=extra_body,
        )
        payload = request.model_dump(mode="json", exclude_none=True)
        payload["stream"] = True

        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        url = f"{self.base_url}/chat/completions"
        logger.info(f"Making streaming POST request to {url}")

        async with (
            httpx.AsyncClient(timeout=self.timeout) as http_client,
            http_client.stream(
                "POST",
                url,
                json=payload,
                params={"project_id": project_id},
                headers=headers,
            ) as response,
        ):
            await self._raise_for_streaming_status(response)
            async for line in response.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[len("data:") :].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk_payload = json.loads(data)
                except ValueError as e:
                    raise TesseraError(
                        f"[{self.__class__.__name__}] /chat/completions: "
                        f"received a malformed streaming chunk: {e}"
                    ) from e
                yield ChatCompletionChunk(**chunk_payload)

    async def _raise_for_streaming_status(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        await response.aread()
        class_name = self.__class__.__name__
        try:
            detail = response.json().get("detail")
        except (ValueError, KeyError, AttributeError):
            detail = response.text
        if response.status_code == 401:
            raise TesseraAuthenticationError(
                f"[{class_name}] /chat/completions: {detail or 'Authentication failed'}"
            )
        if response.status_code == 404:
            raise TesseraNotFoundError(
                f"[{class_name}] /chat/completions: {detail or 'Resource not found'}"
            )
        if response.status_code == 400:
            raise TesseraValidationError(
                f"[{class_name}] /chat/completions: {detail or 'Bad request'}"
            )
        if 400 <= response.status_code < 500:
            raise TesseraClientError(
                f"[{class_name}] /chat/completions: {response.status_code} {detail}",
                response.status_code,
            )
        if 500 <= response.status_code < 600:
            raise TesseraServerError(
                f"[{class_name}] Server error: {response.status_code}",
                response.status_code,
            )
        raise TesseraError(
            f"[{class_name}] Unexpected status code: {response.status_code}"
        )

    def scan_file(
        self,
        file_url: str,
        mime_type: Optional[str] = None,
        model: Optional[str] = None,
        project_id: str = "*",
    ) -> ScanResponse:
        request = ScanFileRequest(
            file_url=file_url,
            mime_type=mime_type,
            model=model,
        )
        response = self._make_request(
            HTTPMethods.POST,
            "/scan/file",
            data=request.model_dump(mode="json", exclude_none=True),
            params={"project_id": project_id},
        )
        return ScanResponse(**response.json())

    def summarize_text(
        self,
        content: str,
        model: Optional[str] = None,
        project_id: str = "*",
    ) -> SummarizeResponse:
        request = SummarizeTextRequest(
            content=content,
            model=model,
        )
        response = self._make_request(
            HTTPMethods.POST,
            "/summarize/text",
            data=request.model_dump(mode="json", exclude_none=True),
            params={"project_id": project_id},
        )
        return SummarizeResponse(**response.json())

    def summarize_file(
        self,
        file_url: str,
        mime_type: Optional[str] = None,
        model: Optional[str] = None,
        project_id: str = "*",
    ) -> SummarizeResponse:
        request = SummarizeFileRequest(
            file_url=file_url,
            mime_type=mime_type,
            model=model,
        )
        response = self._make_request(
            HTTPMethods.POST,
            "/summarize/file",
            data=request.model_dump(mode="json", exclude_none=True),
            params={"project_id": project_id},
        )
        return SummarizeResponse(**response.json())
