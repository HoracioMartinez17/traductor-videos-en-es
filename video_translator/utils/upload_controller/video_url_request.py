from pydantic import BaseModel

class VideoUrlRequest(BaseModel):
    url: str
