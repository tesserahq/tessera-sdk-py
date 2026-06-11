from typing import Any

from pydantic import BaseModel


class ScanResponse(BaseModel):
    data: dict[str, Any]
    model: str
    request_id: str
