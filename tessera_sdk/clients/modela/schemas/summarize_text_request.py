from typing import Optional

from pydantic import BaseModel


class SummarizeTextRequest(BaseModel):
    content: str
    model: Optional[str] = None
