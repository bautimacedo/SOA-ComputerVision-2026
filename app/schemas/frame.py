from pydantic import BaseModel, ConfigDict
from typing import Any
from uuid import UUID


class FrameSearchResult(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "frameId": "550e8400-e29b-41d4-a716-446655440000",
            "imageURL": "https://soagmr.mooo.com/frames/550e8400-e29b-41d4-a716-446655440000",
            "metadata": {"lat": -34.6037, "lon": -58.3816, "camara": "cam_01"},
            "detections": [
                {"objects": [{"class": "person", "confidence": 0.91, "bbox": [34.0, 45.0, 216.0, 328.0]}]}
            ]
        }
    })

    frameId: UUID
    imageURL: str
    metadata: dict[str, Any]
    detections: list[dict[str, Any]]
