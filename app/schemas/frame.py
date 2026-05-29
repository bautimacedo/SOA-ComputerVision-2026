from pydantic import BaseModel
from typing import Any
from uuid import UUID


class FrameSearchResult(BaseModel):
    frameId: UUID
    imageURL: str
    metadata: dict[str, Any]
    detections: list[dict[str, Any]]
