import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx
import requests

from ...config import get_settings
from ...constants import HTTPMethods
from ...infra.events import Event
from ...mcp import CompletionInclude
from .._base.client import BaseClient
from .._base.exceptions import TesseraError
from .exceptions import _ModelaErrorFactory
from .schemas.chat_completion_chunk import ChatCompletionChunk
from .schemas.chat_completion_extensions import ChatCompletionExtensions
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
        base_url: str | None = None,
        api_token: str | None = None,
        timeout: int | None = None,
        session: requests.Session | None = None,
        stream_read_timeout: float | None = None,
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

        # `timeout` above governs connect/write/pool for both the sync
        # (requests) client used by `complete` and the streaming client
        # below. It intentionally does NOT bound how long `stream_complete`
        # may wait between chunks: a streamed completion can legitimately
        # go quiet for tens of seconds between tokens (long generations,
        # tool calls, backend load), and reusing `timeout` as the read
        # timeout there causes spurious httpx.ReadTimeout failures mid-stream.
        self.stream_read_timeout = (
            float(stream_read_timeout)
            if stream_read_timeout is not None
            else float(get_settings().tesserasdk_modela_stream_read_timeout)
        )

    def complete(
        self,
        messages: list[CompletionMessage],
        model: str | None = None,
        extra_body: dict[str, Any] | None = None,
        include: list[CompletionInclude] | None = None,
        project_id: str = "*",
    ) -> ChatCompletionResponse:
        request = ChatCompletionRequest(
            messages=messages,
            model=model,
            extra_body=extra_body,
            include=include,
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
        model: str | None = None,
        extra_body: dict[str, Any] | None = None,
        include: list[CompletionInclude] | None = None,
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
            include=include,
        )
        payload = request.model_dump(mode="json", exclude_none=True)
        payload["stream"] = True

        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        url = f"{self.base_url}/chat/completions"
        logger.info(f"Making streaming POST request to {url}")

        stream_timeout = httpx.Timeout(
            connect=self.timeout,
            read=self.stream_read_timeout,
            write=self.timeout,
            pool=self.timeout,
        )

        async with (
            httpx.AsyncClient(timeout=stream_timeout) as http_client,
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
            payload = response.json()
            detail = payload.get("detail")
        except (ValueError, KeyError, AttributeError):
            payload = {}
            detail = response.text
        events = self._events_from_payload(payload)
        raise _ModelaErrorFactory.from_http_status(
            status_code=response.status_code,
            context=f"[{class_name}] /chat/completions",
            detail=detail,
            events=events,
        )

    def _prepare_http_error(
        self, error: TesseraError, response: requests.Response
    ) -> TesseraError:
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        events = self._events_from_payload(payload)
        return _ModelaErrorFactory.from_tessera_error(error, events)

    @staticmethod
    def _events_from_payload(payload: Any) -> tuple[Event, ...]:
        try:
            extensions = ChatCompletionExtensions.model_validate(
                (payload or {}).get("extensions", {})
            )
        except (AttributeError, ValueError):
            return ()
        return tuple(extensions.events)

    def scan_file(
        self,
        file_url: str,
        mime_type: str | None = None,
        model: str | None = None,
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
        model: str | None = None,
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
        mime_type: str | None = None,
        model: str | None = None,
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
