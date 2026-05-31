from pydantic import BaseModel, ConfigDict
from typing import Any
from uuid import UUID


class DetectionResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "frameId": "550e8400-e29b-41d4-a716-446655440000",
            "modelId": "yolo11n.pt",
            "detections": [
                {"class": "person", "confidence": 0.91, "bbox": [34.0, 45.0, 216.0, 328.0]},
                {"class": "zebra",  "confidence": 0.87, "bbox": [100.0, 80.0, 520.0, 410.0]},
            ]
        }
    })

    frameId: UUID
    modelId: str
    detections: list[dict[str, Any]]
