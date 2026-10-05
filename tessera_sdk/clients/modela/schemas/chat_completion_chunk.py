from pydantic import BaseModel, field_validator

from .chat_completion_extensions import (
    ChatCompletionChunkExtensions,
    _validate_optional,
)


class ChatCompletionChunkDelta(BaseModel):
    role: str | None = None
    content: str | None = None


class ChatCompletionChunkChoice(BaseModel):
    index: int
    delta: ChatCompletionChunkDelta
    finish_reason: str | None = None


class ChatCompletionChunk(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: list[ChatCompletionChunkChoice]
    extensions: ChatCompletionChunkExtensions | None = None

    @field_validator("extensions", mode="wrap")
    @classmethod
    def _drop_invalid_extensions(cls, value, handler):
        return _validate_optional("extensions", value, handler)
