from typing import Optional

from pydantic import BaseModel


class DownloadRequest(BaseModel):
    url: str
    api_key: Optional[str] = None
    model_type: str = "loras"
    filename: Optional[str] = None
