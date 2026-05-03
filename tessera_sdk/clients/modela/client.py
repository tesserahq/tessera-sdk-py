import logging
from typing import Any, Optional
import requests

from .._base.client import BaseClient
from ...constants import HTTPMethods
from ...config import get_settings
from .schemas.chat_completion_request import ChatCompletionRequest, CompletionMessage
from .schemas.chat_completion_response import ChatCompletionResponse

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
