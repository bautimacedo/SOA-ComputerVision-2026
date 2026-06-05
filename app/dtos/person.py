from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import Any
from uuid import UUID


class PersonCreate(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "nombre": "Juan",
            "apellido": "Pérez",
            "email": "juan@mail.com",
            "extra": {"legajo": "12345", "sector": "seguridad"}
        }
    })

    nombre: str
    apellido: str
    email: EmailStr
    extra: dict[str, Any] | None = None


class PersonResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "personId": "550e8400-e29b-41d4-a716-446655440000",
                "nombre": "Juan",
                "apellido": "Pérez",
                "email": "juan@mail.com",
                "extra": {"legajo": "12345"}
            }
        }
    )

    personId: UUID = Field(alias="id")
    nombre: str
    apellido: str
    email: str
    extra: dict[str, Any] | None = None


class EmbeddingResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "personId": "550e8400-e29b-41d4-a716-446655440000",
            "processedImages": 3,
            "validEmbeddings": 2,
            "rejectedImages": 1
        }
    })

    personId: UUID
    processedImages: int
    validEmbeddings: int
    rejectedImages: int


class RecognitionResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "personId": "550e8400-e29b-41d4-a716-446655440000",
            "nombre": "Juan",
            "apellido": "Pérez",
            "confidence": 0.87
        }
    })

    personId: UUID | None
    nombre: str | None = None
    apellido: str | None = None
    confidence: float
