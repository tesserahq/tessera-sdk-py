from pydantic import BaseModel

from .chat_completion_extensions import ChatCompletionExtensions


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
