from pydantic import BaseModel, field_validator

from .chat_completion_extensions import ChatCompletionExtensions, _validate_optional


class CompletionMessage(BaseModel):
    role: str
    content: str


class CompletionChoice(BaseModel):
    index: int
    message: CompletionMessage
    finish_reason: str


class CompletionUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: list[CompletionChoice]
    usage: CompletionUsage
    extensions: ChatCompletionExtensions | None = None

    @field_validator("extensions", mode="wrap")
    @classmethod
    def _drop_invalid_extensions(cls, value, handler):
        return _validate_optional("extensions", value, handler)
