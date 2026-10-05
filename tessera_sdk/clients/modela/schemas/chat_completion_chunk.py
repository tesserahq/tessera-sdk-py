from pydantic import BaseModel

from .chat_completion_extensions import ChatCompletionChunkExtensions


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
