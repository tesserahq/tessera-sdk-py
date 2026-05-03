from pydantic import BaseModel
from typing import Any, Optional


class CompletionMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    messages: list[CompletionMessage]
    model: Optional[str] = None
    extra_body: Optional[dict[str, Any]] = None
