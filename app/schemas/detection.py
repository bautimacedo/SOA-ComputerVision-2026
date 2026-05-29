from pydantic import BaseModel
from typing import Any
from uuid import UUID


class DetectionResponse(BaseModel):
    frameId: UUID
    modelId: str
    detections: list[dict[str, Any]]
