from typing import Any

from pydantic import BaseModel, model_validator

from ....mcp import CompletionInclude


class CompletionMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    messages: list[CompletionMessage]
    model: str | None = None
    include: list[CompletionInclude] | None = None
    extra_body: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_include_sources(self):
        nested = (self.extra_body or {}).get("include")
        if self.include is None or nested is None:
            return self
        top_level = [value.value for value in self.include]
        if top_level != nested:
            raise ValueError("include conflicts with extra_body.include")
        return self
