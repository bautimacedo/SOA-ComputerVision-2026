from pydantic import BaseModel, ConfigDict
from typing import Any
from uuid import UUID

# BaseModel es de pydantic. Cuando fastapi ve response_model=DetectionResponse, al final de la función toma lo que devolvés, 
# lo pasa por Pydantic, y Pydantic valida que los tipos sean correctos y lo serealiza a json automaticamente.
class DetectionResponse(BaseModel):
    #esto solo es para swagger
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "frameId": "550e8400-e29b-41d4-a716-446655440000",
            "modelId": "yolo11n.pt",
            "detections": [
                {"class": "person", "confidence": 0.91, "bbox": [0.0531, 0.0937, 0.3375, 0.6833]},
                {"class": "zebra",  "confidence": 0.87, "bbox": [0.1562, 0.1667, 0.8125, 0.8542]},
            ]
        }
    })

    # Esto es lo que va a devolver.
    frameId: UUID
    modelId: str
    detections: list[dict[str, Any]]
