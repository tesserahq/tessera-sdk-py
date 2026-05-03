from pydantic import BaseModel


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
