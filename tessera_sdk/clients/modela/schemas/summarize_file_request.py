from typing import Optional

from pydantic import BaseModel


class SummarizeFileRequest(BaseModel):
    file_url: str
    mime_type: Optional[str] = None
    model: Optional[str] = None
